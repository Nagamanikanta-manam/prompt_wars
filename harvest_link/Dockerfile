# Use the official Python lightweight image
FROM python:3.11-slim

# Allow statements and log messages to immediately appear in the Knative logs
ENV PYTHONUNBUFFERED True

# Set the working directory
WORKDIR /app

# Copy local code to the container image
COPY . ./

# Install production dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Use the built-in ADK server by executing agent.py
# Cloud Run automatically sets the $PORT environment variable
CMD ["python", "agent.py"]
