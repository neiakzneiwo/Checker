#!/bin/bash

# Load environment variables from .env file
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Start the captcha solver API server
python start_solver.py --host 0.0.0.0 --port 12000 --debug --threads 2 --browser camoufox