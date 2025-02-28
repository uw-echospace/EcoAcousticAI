# Use a base Python image
FROM python:3.10-slim


# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    ffmpeg \
    libsndfile1 \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install ExifTool (required for metadata extraction)
RUN apt-get update && apt-get install -y libimage-exiftool-perl

# Set work directory
WORKDIR /app
COPY . .

RUN ls -l /app/bat-detect-msds/src/models/bat_call_detector/bat_detect2/

RUN pip install --no-cache-dir -r /app/bat-detect-msds/requirements.txt

# Expose necessary ports if applicable (e.g., API, web server)
# EXPOSE 8000

# Run the bat-detect MSDS script (or entry point) when the container starts\

CMD ["python3", "src/batdt2_pipeline.py"]

