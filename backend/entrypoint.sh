#!/bin/sh

# Initialize the database
python app/db.py || exit 1

# Start the backend server
uvicorn app.main:app --reload --host 0.0.0.0 --port 5050 --proxy-headers --use-colors --log-level info
