from fastapi import FastAPI, File
from pydantic import BaseModel
from queue_manager import QueueManager

ENQUEUE_URL = '/enqueue'
PULL_URL = '/pullCompleted'
STATUS = '/status'
app = FastAPI()


class BinaryData(BaseModel):
    data: bytes


@app.put(path=ENQUEUE_URL)
async def enqueue(iterations: int, data: bytes = File()):
    jobInstance = QueueManager().enqueue(iterations=iterations, data=data)
    return {'Work ID': jobInstance.id}


@app.post(path=PULL_URL)
async def pullCompleted(top: int):
    return QueueManager().getCompleted(limit=top)


@app.get(path=STATUS)
async def status():
    queue = QueueManager()
    return {'Jobs': queue.getSize(), 'Workers': queue.getNumOfWorkers()}

