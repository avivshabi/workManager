import os
from redis import RedisCluster
from rq import Queue, job, Connection, Worker
from worker import work


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
        return self._queue.enqueue(work, iterations=iterations, buffer=data, result_ttl=-1)

    def getCompleted(self, limit):
        results = []

        if limit > 0:
            with Connection():
                jobIds = self._completed.get_job_ids()[-limit:]

                for jobId in jobIds:
                    results.append(
                        {
                            'Word ID': jobId,
                            'Value': job.Job.fetch(id=jobId).result.hex()
                        })

        return results

    def isEmpty(self):
        return self._queue.is_empty()

    def getSize(self):
        return len(self._queue.jobs)

    def getNumOfWorkers(self):
        return Worker.count(queue=self._queue)
