FROM python:3.12-slim

WORKDIR /app

# Copy the requirements.txt file to the container
COPY requirements.txt /tmp/requirements.txt

# Install Python dependencies
RUN pip install -r /tmp/requirements.txt \
    --no-cache-dir --break-system-packages --root-user-action=ignore

# Set environment variables
ENV PORT=8080
ENV FLASK_DEBUG=0

# No COPY commands for application files as they're mounted as volumes
# in docker-compose.slack.yml for development

EXPOSE 8080

# Run the server
CMD ["python", "slack_server.py"]
