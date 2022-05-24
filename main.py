from fastapi import FastAPI
from pydantic import BaseModel

import redis_queue
from worker import work
from rq import job
from rq.registry import FinishedJobRegistry

ENQUEUE_URL = '/enqueue'
PULL_URL = '/pullCompleted'

app = FastAPI()


class BinaryData(BaseModel):
    data: str


@app.put(path=ENQUEUE_URL)
async def enqueue(iterations: int, buffer: BinaryData):
    jobInstance = redis_queue.queue.enqueue(work, iterations=iterations, buffer=buffer, results_ttl=-1)
    return {'Work ID': jobInstance.id}


@app.post(path=PULL_URL)
async def pullCompleted(top: int):
    jobIds = FinishedJobRegistry(connection=redis_queue.connection).get_job_ids()[-top:]
    results = []

    for jobId in jobIds:
        results.append(
            {
                'Word ID': jobId,
                'Value': job.Job.fetch(id=jobId).result
            })

    return results
