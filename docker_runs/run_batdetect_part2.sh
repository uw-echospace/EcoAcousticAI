#!/bin/bash

# Loop through each directory in the array
while IFS= read -r directory; do
  echo "Running Docker on directory: $directory"

  if [ -z "$(ls -A "$directory")" ]; then
      echo "Skipping empty directory."
      continue
  fi

files=($(find "$directory" -type f))  # List of all files in the directory
total_files=${#files[@]}

third_files=$(( total_files / 3 ))  # Size of one third

first_third_end=$(( third_files - 1 ))  #
second_third_end=$(( (2 * third_files) - 1 ))  # Index of the last file in the second third

  # Calculate the midpoint to split the list into two halves
  #half_files=$(( ${#files[@]} / 2 ))  # Get the index for the first half

  # Iterate through the second third of the files
  for ((i=first_third_end+1; i<=second_third_end; i++)); do
    file="${files[$i]}"
    filename=$(basename "$file")  # Get the filename (e.g., 'file.wav')
    if [[ "$filename" == *.WAV ]]; then
        # Rename the file to .WAV
        echo "Running Docker for file: $filename"
    

        # Run Docker command with the full directory mounted
        docker run --rm \
        --mount type=bind,source="$directory",target="/app/recordings_2023/" \
        --mount type=bind,source="/mnt/ecoacoustic-storage/",target="/app/output_dir/" \
        bat-detect-msds:latest python3 /app/bat-detect-msds/src/batdt2_pipeline.py \
        --input_audio="/app/recordings_2023/$filename" \
        --output_directory="/app/output_dir/" --run_model --csv
    else
        echo "Skipping non-WAV file: $filename"
    fi
  done

done < new_directories.txt
