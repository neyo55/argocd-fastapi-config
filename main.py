from fastapi import FastAPI
import os
import socket

app = FastAPI()

@app.get("/")
def read_root():
    hostname = socket.gethostname()
    return {
        "message": "Hello from FastAPI!",
        "version": "2.0 - The Ingress Update",
        "pod_name": hostname,
        "status": "Unkillable App is Running"
    }