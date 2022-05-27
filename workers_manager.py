import os
import sched

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
export RQ_CONNECTION_CLASS="redis.RedisCluster"
export REDIS_HOST={os.environ['HOST_IP']}
git clone https://github.com/avivshabi/workManager.git app
cd app
pip3 install -r requirements.txt --upgrade
python3 worker.py && shutdown -h now
"""

JOBS_PER_WORKER = 10000
LOAD_BALANCE_DELAY = 300
scheduler = sched.scheduler()


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


def balance():
    manager = WorkersManager()
    manager.addWorkers()
    scheduler.enter(delay=LOAD_BALANCE_DELAY, priority=0, action=balance)
    scheduler.run()


if __name__ == '__main__':
    scheduler.enter(delay=0, priority=0, action=balance)
    scheduler.run()
