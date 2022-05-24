import os
from redis import Redis
from rq import Queue, registry, job, Connection
from worker import work


class QueueManager:
    def __init__(self):
        self._conn = Redis(
            host=os.getenv('REDIS_HOST', '127.0.0.1'),
            port=os.getenv('REDIS_PORT', 6379),
            password=os.getenv('REDIS_PASSWORD', '')
        )
        self._queue = Queue(connection=self._conn)
        self._completed = registry.FinishedJobRegistry(connection=self._conn)

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
