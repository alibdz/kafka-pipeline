import sys, os
import multiprocessing

from image_adder.single_adder import adder
from image_adder.file_config import read_config

config = read_config('image_adder/config.ini')
num_processes=config.getint("service","num_processes")

def main():
    processes = [multiprocessing.Process(target=adder) 
                 for i in range(num_processes)]
    for process in processes:
        process.start()
    for process in processes:
        process.join()
        
if __name__ == '__main__':
    main()
