#!/bin/bash

# Loop through each directory in the array
while IFS= read -r directory; do
  echo "Running Docker on directory: $directory"

  if [ -z "$(ls -A "$directory")" ]; then
      echo "Skipping empty directory."
      continue
  fi

  # Get a list of all files in the directory
  files=($(find "$directory" -type f))  # List of all files in the directory

  # Calculate the midpoint to split the list into two halves
  half_files=$(( ${#files[@]} / 2 ))  # Get the index for the first half

  # Iterate through the second half of the files
  for ((i=$half_files; i<${#files[@]}; i++)); do
    file="${files[$i]}"
    filename=$(basename "$file")  # Get the filename (e.g., 'file.wav')

    echo "Running Docker for file: $filename"

    # Run Docker command with the full directory mounted
    docker run --rm \
      --mount type=bind,source="$directory",target="/app/recordings_2023/" \
      --mount type=bind,source="/mnt/ecoacoustic-storage/",target="/app/output_dir/" \
      bat-detect-msds:latest python3 /app/bat-detect-msds/src/batdt2_pipeline.py \
      --input_audio="/app/recordings_2023/$filename" \
      --output_directory="/app/output_dir/" --run_model --csv
  done

done < new_directories.txt
