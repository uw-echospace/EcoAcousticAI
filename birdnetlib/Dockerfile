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
COPY . .


RUN pip install --no-cache-dir -r requirements.txt

# Expose necessary ports if applicable (e.g., API, web server)
# EXPOSE 8000

# Run the bat-detect MSDS script (or entry point) when the container starts\

CMD ["python3", "predict_frog_species.py"]

