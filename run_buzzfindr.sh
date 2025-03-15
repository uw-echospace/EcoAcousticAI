#!/bin/bash

# Loop through each directory in the array
while IFS= read -r directory; do
  echo "Running Docker on directory:" $directory

  if [ -z "$(ls -A "$directory")" ]; then
      echo "Skipping empty directory."
      continue
  fi

  # Run Docker for each directory
    docker run --rm \
        --mount type=bind,source=$directory,target=/app/recordings_buzz/ \
        --mount type=bind,source=/mnt/ecoacoustic-storage/,target=/app/output_buzz/ \
        buzzfindr-image:latest

    # Remove Buzz_Results_ directories after processing
    sudo rm -rf $directory/Buzz_Results_*

done < new_directories.txt