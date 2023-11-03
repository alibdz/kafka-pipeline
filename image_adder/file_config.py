import configparser

def write_config(path=None):
    config = configparser.ConfigParser()
    config['Service'] = {
        "server_ip": "192.168.1.10",
        "service_port": "8001",
        "consumer_topic": "mlengine-raw",
        "producer_topic":"mlengine-processed",
        "external_service_addr": ["192.168.1.101","8002","/api/v2/image"],
        "num_processes": 5
    }
    config['consumer_config'] = {
        "bootstrap.servers": "192.168.1.10:9092",
        "group.id": "test",
        "auto.offset.reset": "latest",
        "enable.auto.commit": "false",
    }
    config['producer_config'] = {
        "bootstrap.servers": "192.168.1.11:9092"
    }
    if not path:
        path = "image_adder/config.ini"
    with open (path, "w") as configfile:
        config.write(configfile)
        
def read_config(path=None):
    config = configparser.ConfigParser()
    if not path:
        path = "config.ini"
    config.read(path)
    return config

def read_kwargs(section):
    dic = {}
    for k in section.keys():
        dic.update({k:section[k]})
    return dic

def print_config(config):
    sections = []
    for s in config.sections():
        sections.append(config[s])
    for section in sections:
        for key in section:
            print(f"{key} = {section.get(key)}")

if __name__=="__main__":
    print_config(read_config())
