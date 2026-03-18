#!/bin/bash
gunicorn --workers 2 --timeout 120 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 app:app
