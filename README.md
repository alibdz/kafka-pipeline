# Real-Time Enrichment Pipeline (v0.1.0)

**Table of contents**
- [Description](#description)
- [How to run (local)](#how-to-run-local)
  * [Create virtual environment](#create-virtual-environment)
  * [Get the code](#get-the-code)
  * [Install requirements](#install-requirements)
- [How to run (Docker)](#how-to-run-docker)
  * [Install Docker and docker-compose](#install-docker-and-docker-compose)
  * [Build and Run](#Build-the-image)


## Description
This repository provides a real-time image enrichment pipeline for ML engine events using Confluent Kafka. The pipeline consumes high volume event streams from Kafka topics and enriches the messages by fetching relevant image frames using timestamps. It uses queues and multiple threads for scalable asynchronous processing.

For each event message, the pipeline extracts the timestamp and schedules an asynchronous API call to fetch the image. The pending calls are tracked in a queue. As responses arrive, another queue holds the enriched messages ready for output. The pipeline is multi-threaded to enable concurrent consumption, API calls and production for high throughput. It leverages Confluent Kafka's scalable pub-sub messaging system for the event streams and enriched output topic. Downstream consumers receive augmented messages with relevant images for further processing. This allows real-time correlation of AI events with visual data.

## How to run (local)

**Prerequisites:**
- python>=3.8
- confluent_kafka
- pydantic
- requests

### Create virtual environment
To isolate dependencies, create and activate a new virtual environment using venv:
```bash
python3 -m venv path/to/virtualenv
source path/to/virtualenv/bin/activate
```
### Get the code
Clone the repository and change directory using:

```bash
git clone https://github.com/alibdz/kafka-pipeline.git
cd kafka-pipeline
```
In `config.ini`, set the `server_ip` and `service_port` fields to match your environment:
```bash
[service]
server_ip = 192.168.1.10
service_port = 8001
consumer_topic = mlengine-raw
producer_topic = mlengine-processed
desired_objects = type1, type2
cm_addr = 192.168.1.101, 8002, /api/v2/image
num_processes = 5

[consumer_config]
bootstrap.servers = 192.168.1.10:9092
group.id = test
auto.offset.reset = latest
enable.auto.commit = false

[producer_config]
bootstrap.servers = 192.168.1.11:9092
```
You can also modify other configuration values in `config.ini` as needed.

### Install requirements
install python packages using:

```bash
python -m install --upgrade pip
pip install -r requirements.txt
```

To run the service execute the following command:
```bash
python main.py 
```

## How to run (Docker)

**Prerequisites:**

- Docker
- docker-compose

### Install Docker and docker-compose
Install Docker by following the [official installation guide](https://docs.docker.com/engine/install/ubuntu/). Verify the installation was successful with:

```bash
sudo systemctl status docker # or
sudo docker --version
```
Install docker-compose by following the [DigitalOcean guide]((https://www.digitalocean.com/community/tutorials/how-to-install-and-use-docker-compose-on-ubuntu-20-04)). Refer to the [latest stable release](https://github.com/docker/compose/releases) - version 2.23.0 at the time of writing. Verify the installation with:
```bash
docker-compose --version
```


### Build the image
You can build the image using:
```bash
sudo docker-compose build
```

### Run the service
Run it using:
```bash
sudo docker-compose up
```

### Current version
#### 0.1.0
  - Implemented a multiprocess runner to improve latency and reduce lag.
  - Added a configuration file for customizable settings.

### Known Issues
- Misconfigured Kafka broker settings can cause problems with subscription and polling on startup.
