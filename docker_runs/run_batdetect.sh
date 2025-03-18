#!/bin/bash

# Loop through each directory in new_directories.txt
while IFS= read -r directory; do
  echo "Running Docker on directory:" $directory

  if [ -z "$(ls -A "$directory")" ]; then
      echo "Skipping empty directory."
      continue
  fi
files=($(find "$directory" -type f))  # List of all files in the directory

  # Iterate through all of the files to check whether they are .WAV format
  for ((i=0; i<${#files[@]}; i++)); do
    file="${files[$i]}"
    filename=$(basename "$file")  # Get the filename

    # Check if the file ends with .WAV 
    if [[ "$filename" == *.WAV ]]; then
        echo "Running Docker for file: $filename"


        # Run the second Docker command for bat-detect-msds processing
        docker run --rm \
            --mount type=bind,source=$directory,target=/app/recordings_2023/ \
            --mount type=bind,source=/mnt/ecoacoustic-storage,target=/app/output_dir/ \
            bat-detect-msds:latest python3 /app/bat-detect-msds/src/batdt2_pipeline.py \
            --input_audio="/app/recordings_2023/$filename" \
            --output_directory="/app/output_dir/" --run_model --csv
    else
        echo "Skipping non-WAV file: $filename"
    fi
    
  done

done < new_directories.txt