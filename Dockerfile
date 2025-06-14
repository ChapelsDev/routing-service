# Start from a lightweight Python image
FROM python:3.10-slim

# Set a working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

RUN apt-get update && \
    apt-get install -y --no-install-recommends netcat-openbsd && \
    rm -rf /var/lib/apt/lists/*


# Copy the rest of your app's source code (including seed.py and entrypoint.sh)
COPY . .

# Create the directory for the SQLite database
RUN mkdir -p /app/data

# Expose Flask's default port (adjust if you’re using a different port)
EXPOSE 5000

# Ensure the entrypoint script is executable
RUN chmod +x entrypoint.sh

# Set the entrypoint to run the startup script
ENTRYPOINT ["./entrypoint.sh"]
