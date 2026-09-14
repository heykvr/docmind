import os
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.environ["REDIS_URL"]

app = Celery("docmind", broker=REDIS_URL, backend=REDIS_URL, include=["tasks"])
app.conf.task_serializer = "json"
app.conf.result_serializer = "json"
app.conf.accept_content = ["json"]
app.conf.task_track_started = True
