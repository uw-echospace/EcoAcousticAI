#!/bin/bash

# Define the directory to search
DIR="/mnt/ecoacoustic-storage"

# Loop through files in the directory and its subdirectories
find "$DIR" -type f \( -name "*.selection.txt" -o -name "*.species.csv" \) | while read file; do
    echo "Changing owner of: $file"
    sudo chown ubuntu:ubuntu "$file"
done

echo "Ownership changes complete."
