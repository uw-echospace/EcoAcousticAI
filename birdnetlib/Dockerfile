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


# Set work directory
WORKDIR /app

# copy contents of current direcotry (birdnetlib) to /app
COPY . .

# create direcotry to mount input audio 
RUN mkdir -p /app/audio/

# install requirements 
RUN pip install --no-cache-dir -r requirements.txt

# execute permission for entrypoint script
RUN chmod +x run_both_models.sh

ENTRYPOINT ["/app/run_both_models.sh"]
