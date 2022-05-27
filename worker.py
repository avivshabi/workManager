import os
import sched

from redis import RedisCluster
from rq import Worker, Queue, Connection

ATTEMPTS = 10
WORKERS_DELAY = 45
listen = ['high', 'default', 'low']
scheduler = sched.scheduler()
conn = RedisCluster(
    host=os.getenv('REDIS_HOST', '0.0.0.0'),
    port=os.getenv('REDIS_PORT', 6379),
    password=os.getenv('REDIS_PASSWORD', ''),
)
worker = Worker(map(Queue, listen))


def execute(attempts=-1):
    global worker

    if attempts < 0:
        return

    with Connection(connection=conn):
        scheduler.enter(
            delay=WORKERS_DELAY,
            priority=0,
            action=execute,
            kwargs={
                'attempts': (ATTEMPTS if worker.work(burst=True) else attempts - 1)
            }
        )
        scheduler.run()


if __name__ == '__main__':
    scheduler.enter(
        delay=0,
        priority=0,
        action=execute,
        kwargs={
            'attempts': ATTEMPTS
        }
    )
    scheduler.run()
