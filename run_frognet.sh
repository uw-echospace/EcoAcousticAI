#!/bin/bash

# # Loop through each directory in the array
# while IFS= read -r directory; do
#   echo "Running Docker on directory:" $directory

#   if [ -z "$(ls -A "$directory")" ]; then
#       echo "Skipping empty directory."
#       continue
#   fi

#   # Run Docker for each directory
#     docker run --rm \
#         --mount type=bind,source=$directory,target=/app/frog_audio/ \
#         --mount type=bind,source=/mnt/ecoacoustic-storage/,target=/app/results/frogs/ \
#         frognet:latest

# done < new_directories.txt

 docker run --rm \
        --mount type=bind,source=/tmp/osn_bucket/,target=/app/audio/ \
        --mount type=bind,source=/mnt/ecoacoustic-storage/,target=/app/results/frogs/ \
        --mount type=bind,source=/mnt/ecoacoustic-storage/,target=/app/results/birdnet_wa_all/ \
        frog_bird:latest