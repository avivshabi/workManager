import os
from redis import RedisCluster
from rq import Queue, job, Worker, Connection
from rq.registry import FinishedJobRegistry
from hash import compute


class QueueManager:
    def __init__(self):
        self._conn = RedisCluster(
            host=os.getenv('REDIS_HOST', '0.0.0.0'),
            port=os.getenv('REDIS_PORT', 6379),
            password=os.getenv('REDIS_PASSWORD', ''),
        )
        self._queue = Queue(connection=self._conn)

    def enqueue(self, iterations: int, data: bytes):
        return self._queue.enqueue(compute, iterations=iterations, buffer=data, result_ttl=-1)

    def getCompleted(self, limit):
        results = []

        for node in self._conn.get_primaries():
            if limit > 0:
                jobIds = FinishedJobRegistry(connection=node.redis_connection).get_job_ids()[-limit:]

                for jobId in jobIds:
                    results.append({
                        'Work ID': jobId,
                        'Value': job.Job.fetch(id=jobId).result.hex()
                    })

        if len(results) > limit:
            results = results[:limit]

        return results

    def isEmpty(self):
        return self._queue.is_empty()

    def getSize(self):
        return len(self._queue.jobs)

    def getNumOfWorkers(self):
        return Worker.count(queue=self._queue)
