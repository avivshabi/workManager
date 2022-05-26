import os
import boto3
from requests import get
from queue_manager import QueueManager
from dotenv import load_dotenv

load_dotenv()

if 'HOST_IP' not in os.environ:
    os.environ['HOST_IP'] = get('https://api.ipify.org').content.decode('utf8')

userData = f"""#!/bin/bash
sudo apt -y update
sudo apt -y install python3-pip
sudo apt -y install python3-rq
export RQ_CONNECTION_CLASS="redis.RedisCluster"
export REDIS_HOST={os.environ['HOST_IP']}
git clone https://github.com/avivshabi/workManager.git app
cd app
python worker.py
shutdown -h now
"""

JOBS_PER_WORKER = 10000


class WorkersManager:
    def __init__(self):
        self._queueManager = QueueManager()

    def burstsNeeded(self):
        return (not self._queueManager.isEmpty() and
                self._queueManager.getSize() / JOBS_PER_WORKER > self._queueManager.getNumOfWorkers())

    def numOfBurstsNeeded(self):
        left = self._queueManager.getSize()

        if left < JOBS_PER_WORKER:
            return 1

        return left // JOBS_PER_WORKER

    def addWorkers(self):
        if self.burstsNeeded():
            count = self.numOfBurstsNeeded()
            boto3.client('ec2').run_instances(
                ImageId='ami-09d56f8956ab235b3',
                InstanceType='t2.micro',
                MinCount=count,
                MaxCount=count,
                UserData=userData,
                InstanceInitiatedShutdownBehavior='terminate')


if __name__ == '__main__':
    manager = WorkersManager()
    manager.addWorkers()
