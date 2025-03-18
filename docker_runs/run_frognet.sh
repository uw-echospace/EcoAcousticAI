#!/bin/bash
# Loop through directories in new_directories.txt
while IFS= read -r directory; do
  echo "Running Docker on directory:" $directory

  # skip empty directories 
  if [ -z "$(ls -A "$directory")" ]; then
      echo "Skipping empty directory."
      continue
  fi
  
  # mount input directory to directory in docker container
  # mount manila storage directory (/mnt/ecoacoustic-storage/) to each model output directory
  docker run --rm \
                --mount type=bind,source=$directory,target=/app/audio/ \
                --mount type=bind,source=/mnt/ecoacoustic-storage/,target=/app/results/frogs/ \
                --mount type=bind,source=/mnt/ecoacoustic-storage/,target=/app/results/birdnet_wa_all/ \
                frog_bird:latest

done < new_directories.txt