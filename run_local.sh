#!/bin/bash

# Script to run the Cloud Defender game locally

echo "Starting Cloud Defender game locally..."

# Set environment variable to indicate local mode
export ENVIRONMENT=local

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed. Please install Python 3 to run this application."
    exit 1
fi

# Check if required packages are installed
echo "Checking required packages..."
python3 -m pip install -q flask numpy pygame pillow

# Create assets directory if it doesn't exist
mkdir -p assets

# Run the Flask application
echo "Starting Flask application on http://localhost:8082"
echo "Press Ctrl+C to stop the server"
python3 -c "
import os
from app import app
os.environ['ENVIRONMENT'] = 'local'
app.run(host='0.0.0.0', port=8082, debug=True)
"
