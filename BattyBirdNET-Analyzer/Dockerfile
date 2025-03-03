# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Install dependencies required by webview and for building packages
RUN apt-get update && apt-get install -y \
    pkg-config \
    libgtk-3-dev \
    libwebkit2gtk-4.0-dev \
    gcc \
    make \
    && rm -rf /var/lib/apt/lists/*


# Set the working directory inside the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app


# Install dependencies from the requirements file
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port the app runs on (optional)
# EXPOSE 8080

# Set environment variable (optional)
#ENV PYTHONUNBUFFERED 1

# Command to run the script when the container starts
CMD ["python", "bat_ident.py"]
