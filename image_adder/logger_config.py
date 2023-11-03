import logging
from logging.handlers import RotatingFileHandler
import os
import errno

LOG_MAXBYTES= 100 * 1024 * 1024

def mkdir_prog(path):
    try:
        os.makedirs(path, exist_ok=True)
    except TypeError:
        try:
            os.makedirs(path)
        except OSError as exc:
            if exc.errno == errno.EEXIST and os.path.isdir(path):
                pass
            else: raise

class MakeFileHandler(RotatingFileHandler):
    def __init__(self, filename, mode='a'):
        mkdir_prog(os.path.dirname(filename))
        RotatingFileHandler.__init__(
            self,
            filename,
            mode,
            maxBytes=LOG_MAXBYTES, backupCount=10)

def create_get_logger(
        name, 
        global_level=logging.INFO,create_file_logger=True,
        filename='log/app.log',
        file_logger_level=logging.INFO):
    logger = logging.getLogger(name)
    logger.root.setLevel(global_level)
    if not logger.root.handlers:
        stream_handler = logging.StreamHandler()
        stream_format=logging.Formatter(
            '%(asctime)s - %(filename)s:%(lineno)s - [%(levelname)s] - %(message)s')
        stream_handler.setFormatter(stream_format)
        logger.root.addHandler(stream_handler)

        if create_file_logger==True:
            file_handler = MakeFileHandler(filename, mode='a')
            file_handler.setLevel(file_logger_level)
            file_format=logging.Formatter(
                '%(asctime)s - %(filename)s:%(lineno)s - [%(levelname)s] - %(message)s')
            file_handler.setFormatter(file_format)
            logger.root.addHandler(file_handler)

    return logger