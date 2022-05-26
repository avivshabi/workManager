import os

from redis import RedisCluster
from rq import Worker, Queue, Connection

listen = ['high', 'default', 'low']

conn = RedisCluster(
    host=os.getenv('REDIS_HOST', '0.0.0.0'),
    port=os.getenv('REDIS_PORT', 6379),
    password=os.getenv('REDIS_PASSWORD', ''),
)

if __name__ == '__main__':
    with Connection(connection=conn):
        worker = Worker(map(Queue, listen))
        worker.work()
