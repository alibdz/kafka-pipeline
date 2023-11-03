import confluent_kafka
import concurrent.futures
from datetime import datetime
import json
from pydantic import BaseModel
from queue import Queue
import requests
from typing import Union
from threading import Thread
import os

from .logger_config import create_get_logger
from .file_config import read_config, read_kwargs

config = read_config(os.path.join(os.path.dirname(__file__),'config.ini'))

PRODUCER_TOPIC = config.get('service', 'producer_topic',fallback='mlengine-processed')
CONSUMER_TOPIC = [config.get('service', 'producer_topic',fallback='mlengine-raw')]

DESIRED_OBJECTS = config["service"]["desired_objects"].strip().split(",")
DESIRED_OBJECTS = [o.strip() for o in DESIRED_OBJECTS]

EXT_API = config["service"]["image_service_definition"].strip().split(",")
EXT_API = [i.strip() for i in EXT_API]

consumer_config = read_kwargs(config["consumer_config"])
producer_config = read_kwargs(config["producer_config"])

logger = create_get_logger(__name__)

class ImageRequest(BaseModel):
    id: str
    time_sec: int
    fraction: int
    width: Union[int, None]  = None
    height: Union[int, None] = None
    url: Union [str, None]
    name: Union [str, None]

# Queue for all consumed messages without an image (buffer: null)
publish_queue = Queue(maxsize=100000)

# Queue for consumed messages with an image (buffer: not null)
enrich_queue = Queue(maxsize=1000)

# Queue for modified messages with an added image from external service
outbound_queue = Queue(maxsize=1000)

def iso8601_to_timestamp(iso8601_time: str) -> float:
    """Converts formatted iso8601 timestamp into unix epochtime (ms)

    Args: 
        iso8601_time(str): 
        The formatted timestamp (e.g.: "2023-02-21T14:47:52.079Z")
    
    Returns:
        :py:class:`float` : 
        Epochtime with milisecond precision (e.g.: 1676990872.079)
    """
    utc_dt = datetime.strptime(
        iso8601_time,
        '%Y-%m-%dT%H:%M:%S.%fZ')
    timestamp = (utc_dt - datetime(1970, 1, 1)) \
                .total_seconds()
    return timestamp

class Consumer:
    def __init__(self, configs, loop=None):
        self._consumer = confluent_kafka.Consumer(configs)
        self._consumer.subscribe(CONSUMER_TOPIC)
        self._cancelled = False
        self._consume_thread = Thread(target=self._consume_loop, name="consume_thread")
        self._consume_thread.start()

    def _consume_loop(self):
        while not self._cancelled:
            self.consume()

    def close(self):
        self._cancelled = True
        self._consume_thread.join()

    def consume(self):
        result = self._consumer.poll(0.5)

        if not result:
            logger.warning(f"No message received from {CONSUMER_TOPIC}")
            self.consume()

        if result.error():
            logger.error(f"Error consuming from {CONSUMER_TOPIC}")  
            self.consume()

        message = result.value()

        if is_heartbeat_message(message):
            publish_queue.put(result)
        else:
            message_data = parse_message(message)
            object_type = message_data['objectType']
            object_id = message_data['object']['id']
            
            if is_desired_object(object_type):
                enrich_queue.put(result)
                log_enqueued_message(object_id, enrich_queue)
            else:   
                publish_queue.put(result)

        def is_heartbeat_message(message):
            return '"buffer" : null' in message.decode()

        def parse_message(message):
            return json.loads(message.decode())

        def is_desired_object(object_type):
            return object_type in DESIRED_OBJECTS

        def log_enqueued_message(object_id, queue):
            logger.info(
                f"Enqueued message [{object_id}] to {queue.name}. " 
                f"{queue.name} size: {queue.qsize()}."
            )

class Producer:
    def __init__(self, configs, loop=None):
        self._producer = confluent_kafka.Producer(configs)
        self._cancelled = False
        self._produce_thread = Thread(
            target=self._produce_loop,
            name="produce_thread").start()
        self._produce_enriched_thread = Thread(
            target=self._produce_enriched_loop,
            name="produce_enriched_thread").start()
        self.thread_pool_executor = concurrent.futures.ThreadPoolExecutor(
            thread_name_prefix="image_req")
        self.image_worker = {}
        self._image_thread = Thread(
            target=self._request_image_loop,
            name="image_thread").start()
        self._future_thread = Thread(
            target=self._await_image_loop,
            name="future_thread").start()

    def _request_image_loop(self):
        while not self._cancelled:
            self.request_image()

    def _await_image_loop(self):
        while not self._cancelled:
            self.await_images()
        
    def await_images(self):
        def enrich_message(original, api_result):
            msg = original.copy()
            msg['object'][msg['objectType'].lower()]['buffer'] = api_result.json().get('image')
            return msg

        def log_api_error(original_msg, api_result):
            sensor_id = original_msg['sensor']['id']
            timestamp = get_timestamp(original_msg)
            logger.info(f"Error fetching image for [{sensor_id}]:{timestamp}")

        def get_timestamp(msg):
            ts = repr(iso8601_to_timestamp(msg['@timestamp'])).split('.')
            return f"{ts[0]}.{ts[1]}" 

        def log_enqueued_message(msg):
            timestamp = get_timestamp(msg)
            logger.info(f"Enqueued image {timestamp} to outbound_queue")

        for future in concurrent.futures.as_completed(self.image_worker):
            original_msg = self.image_worker.pop(future)
            api_result = future.result()
            if not api_result.ok:
                log_api_error(original_msg, api_result) 
                continue
            enriched_msg = enrich_message(original_msg, api_result)
            outbound_queue.put(enriched_msg)
            log_enqueued_message(enriched_msg)
        return

    def blocking_image_request(self,msg_dict):
        ts = repr(iso8601_to_timestamp(msg_dict.get("@timestamp"))).split(".")
        sensor_id = msg_dict.get("sensor").get("id")
        image_request = ImageRequest(id=sensor_id, time_sec=int(ts[0]),fraction=int(ts[1]))
        logger.info(msg=f"Requesting image {ts[0]}.{ts[1]} from [{sensor_id}]...")
        endpoint = f"http://{EXT_API[0]}:{EXT_API[1]}{EXT_API[2]}"
        resp = requests.post(endpoint,image_request.json())
        return resp

    def request_image(self):
        msg = enrich_queue.get()
        msg_dict = json.loads(msg.value())
        self.image_worker.update(
            {self.thread_pool_executor.submit(
            self.blocking_image_request,
            msg_dict): msg_dict})

    def _produce_loop(self):
        while not self._cancelled:
            self.produce()
            
    def _produce_enriched_loop(self):
        while not self._cancelled:
            self.produce_enriched()
            
    def close(self):
        self._cancelled = True
        self._produce_enriched_thread.join()
        self._produce_thread.join()
        
    def produce(self):
        msg = publish_queue.get()
        self._producer.produce(PRODUCER_TOPIC,msg.value(),msg.key())
        self._producer.poll(0)
        
    def produce_enriched(self):
        msg_dict = outbound_queue.get()
        key = msg_dict.get("sensor").get("id").encode("utf-8")
        self._producer.produce(PRODUCER_TOPIC, json.dumps(msg_dict).encode("utf-8"), key)
        self._producer.poll(0)

producer = None
consumer = None

def adder():
    global producer, consumer
    consumer = Consumer(consumer_config)
    producer = Producer(producer_config)

if __name__ == '__main__':
    adder()