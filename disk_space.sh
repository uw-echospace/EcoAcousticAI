#!/bin/bash

# Get the total disk space used by Docker images in GB
used_space=$(docker system df --format "{{.ImagesSpace}}" | sed 's/[^0-9]*//g')

# Set the threshold (25 GB)
threshold=25000  # 25 GB in MB

# Compare the used space to the threshold
if [ "$used_space" -gt "$threshold" ]; then
    echo "Docker images are taking up more than 25 GB of space. Running docker image prune -a -f..."
    docker image prune -a -f
else
    echo "Docker images are within the space limit. No action taken."
fi
