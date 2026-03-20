# Use the official Python lightweight image
FROM python:3.11-slim

# Ensure logs are shown immediately in Cloud Run
ENV PYTHONUNBUFFERED=True

# Set working directory
WORKDIR /app

# Copy project files
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Cloud Run uses port 8080
ENV PORT=8080

# Start ADK web server (REQUIRED for Cloud Run)
CMD ["adk", "web", "--host", "0.0.0.0", "--port", "8080"]