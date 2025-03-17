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
#files=($(find "$directory" -type f))  # List of all files in the directory

#   # Calculate the midpoint to split the list into two halves
#   half_files=$(( ${#files[@]} / 2 ))  # Get the index for the first half

#   # Iterate through the first half of the files
#   for ((i=0; i<$half_files; i++)); do
#     file="${files[$i]}"
#     filename=$(basename "$file")  # Get the filename

#     # Check if the file ends with .WAV or .wav
#     if [[ "$filename" == *.WAV ]]; then
#         echo "Running Docker for file: $filename"


#         # Run the second Docker command for bat-detect-msds processing
#         docker run --rm \
#             --mount type=bind,source=$directory,target=/app/recordings_2023/ \
#             --mount type=bind,source=/mnt/ecoacoustic-storage,target=/app/output_dir/ \
#             bat-detect-msds:latest python3 /app/bat-detect-msds/src/batdt2_pipeline.py \
#             --input_audio="/app/recordings_2023/$filename" \
#             --output_directory="/app/output_dir/" --run_model --csv
#     else
#         echo "Skipping non-WAV file: $filename"
#     fi
    
#   done
directory = /tmp/osn_bucket/
files=($(find "$directory" -type f))  # List of all files in the directory

  # Calculate the midpoint to split the list into two halves
  half_files=$(( ${#files[@]} / 2 ))  # Get the index for the first half

  # Iterate through the first half of the files
  for ((i=0; i<$half_files; i++)); do
    file="${files[$i]}"
    filename=$(basename "$file")  # Get the filename

    # Check if the file ends with .WAV or .wav
    if [[ "$filename" == *.WAV ]]; then
        echo "Running Docker for file: $filename"


       docker run --rm \
              --mount type=bind,source=/tmp/osn_bucket/,target=/app/audio/ \
              --mount type=bind,source=/mnt/ecoacoustic-storage/,target=/app/results/frogs/ \
              --mount type=bind,source=/mnt/ecoacoustic-storage/,target=/app/results/birdnet_wa_all/ \
              frog_bird:latest
     else
        echo "Skipping non-WAV file: $filename"
    fi
    done