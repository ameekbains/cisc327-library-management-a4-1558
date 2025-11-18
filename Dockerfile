# Use a small official Python base image
FROM python:3.11-slim

# Ensure output is unbuffered (helpful for logs)
ENV PYTHONUNBUFFERED=1

# Set working directory inside the container
WORKDIR /app

# Install system packages (optional but often needed for common Python deps)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency file first (for better build caching)
COPY requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code (including SQLite DB) into the container
COPY . /app

# --- Flask configuration ---
# Adjust FLASK_APP if your main file is not app.py or your app object is elsewhere.
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=5000

# Expose port 5000 from the container
EXPOSE 5000

# Run the Flask development server (or your own WSGI command if you prefer)
CMD ["flask", "run"]
