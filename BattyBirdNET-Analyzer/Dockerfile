# Use a Python 3.9 slim base image
FROM python:3.9-slim

# Install necessary dependencies for Micromamba
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    bzip2 \
    ca-certificates \
    libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*

# Install Micromamba
RUN wget https://github.com/mamba-org/mamba/releases/download/0.26.0/micromamba-linux-$(uname -m) -O /usr/local/bin/micromamba && \
    chmod +x /usr/local/bin/micromamba

# Set environment variables for Micromamba
ENV MAMBA_ROOT_PREFIX=/opt/micromamba
ENV PATH=$MAMBA_ROOT_PREFIX/bin:$PATH

# Create and activate the environment using micromamba (with conda-forge channel)
RUN micromamba create -y -n myenv python=3.9 numpy scipy librosa resampy ffmpeg sox tensorflow -c conda-forge

# Activate the environment by default
RUN echo "micromamba activate myenv" >> ~/.bashrc

# Copy your Python scripts into the container
COPY . ./

# Set the entrypoint to run your script using the Micromamba environment
CMD ["bash", "-c", "source ~/.bashrc && python3 bat_ident.py"]
