#!/bin/bash

directories=()

# Read each line from new_directories.txt and add it to the array
while IFS= read -r directory; do
  # Skip any empty lines
  if [ -z "$directory" ]; then
    continue
  fi
  directories+=("$directory")  # Add directory to the array
done < new_directories.txt

echo "${directories[@]}"

# Loop through each directory in the array
for directory in "${directories[@]}"; do
  echo "Running Docker on directory: $directory"

  # Check if directory is not empty
  if [ -z "$directory" ]; then
    echo "Skipping empty directory."
    continue
  fi

  # Run Docker for each directory
  docker run --rm \
    --mount type=bind,source=$directory,target=/app/recordings_buzz/ \
    --mount type=bind,source=/ecoacoustic-storage/,target=/app/output_buzz/ \
    buzzfindr-image:latest

  # Remove Buzz_Results_ directories after processing
  sudo rm -rf $directory/Buzz_Results_*

  # Run the second Docker command for bat-detect-msds processing
  docker run --rm \
    --mount type=bind,source=$directory,target=/app/recordings_2023/ \
    --mount type=bind,source=/ecoacoustic-storage/,target=/app/output_dir/ \
    bat-detect-msds:latest python3 /app/bat-detect-msds/src/batdt2_pipeline.py \
    --input_audio='/app/recordings_2023/' \
    --output_directory='/app/output_dir/' --run_model --csv

done < new_directories.txt