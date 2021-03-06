import os
from redis import RedisCluster
from rq import Queue, job, Worker, Connection
from hash import compute


class QueueManager:
    def __init__(self):
        self._conn = RedisCluster(
            host=os.getenv('REDIS_HOST', '0.0.0.0'),
            port=os.getenv('REDIS_PORT', 6379),
            password=os.getenv('REDIS_PASSWORD', ''),
        )
        self._queue = Queue(connection=self._conn)
        self._completed = self._queue.finished_job_registry

    def enqueue(self, iterations: int, data: bytes):
        return self._queue.enqueue(compute, iterations=iterations, buffer=data, result_ttl=-1)

    def getCompleted(self, limit):
        results = []

        with Connection(connection=self._conn):
            if limit > 0:
                jobIds = self._completed.get_job_ids()[-limit:]

                for jobId in jobIds:
                    try:
                        results.append({
                            'Work ID': jobId,
                            'Value': job.Job.fetch(id=jobId).result.hex()
                        })
                    except:
                        continue

        return results

    def isEmpty(self):
        return self._queue.is_empty()

    def getSize(self):
        return len(self._queue.jobs)

    def getNumOfWorkers(self):
        return Worker.count(queue=self._queue)
