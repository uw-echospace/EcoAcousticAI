"""
File Organizer for Manila Storage

This script organizes files in the Manila storage system based on date patterns in filenames.
It dynamically creates date-based directories and moves files into categorized subfolders
to ensure a structured and organized storage environment.

### Features
- Uses regex patterns to match various filename formats.
- Dynamically creates folders for organized file management.
- Handles special cases like 'cumulative_activity' files which are sorted by year.
- Provides clear console output for progress and error handling.

### Expected Folder Structure
/ecoacoustic-storage/
├── YYYYMMDD/
│   ├── batdetect2/
│   ├── buzzfindr/
│   ├── birdnet/
│   ├── frognet/
│   ├── battybirdnet/
│
├── YYYY/
│   ├── cumulative_activity/

### Usage
Run the script directly using:
    python3 move_manila_files.py
"""

import os
import shutil
import re

# Path to Manila storage where files are located
MANILA_STORAGE_PATH = "/ecoacoustic-storage"

# Regex patterns for identifying and classifying files based on their filenames
FILE_PATTERNS = {
    r"batdetect2_pipeline_(\d{8})_\d{6}\.csv": 'batdetect2',         # Matches 'batdetect2' pipeline CSV files
    r"Buzz_Results_(\d{8})_\d{6}\.csv": 'buzzfindr',                 # Matches 'Buzz_Results' CSV files
    r"frognet_(\d{8})_(\d{6})_selection\.txt": 'frognet',             # Matches FrogNet selection text files
    r"frognet_(\d{8})_(\d{6})_species\.csv": 'frognet',               # Matches FrogNet species CSV files
    r"birdnet(\d{8})_(\d{6})_selection\.txt": 'birdnet',             # Matches BirdNet selection text files
    r"birdnet(\d{8})_(\d{6})_species\.csv": 'birdnet',               # Matches BirdNet species CSV files
    r"(\d{8})_(\d{6})\.bat\.results_USA\.csv": 'battybirdnet',        # Matches BattyBirdNET result files
    r"cumulative_activity__\d{4}_.*\.png": 'cumulative_activity'      # Matches cumulative activity plot PNG files
}


def organize_files():
    """
    Organizes files in the Manila storage path by identifying patterns in filenames
    and moving them into structured subdirectories based on their date and type.
    """

    # Check if the Manila storage path exists
    if not os.path.exists(MANILA_STORAGE_PATH):
        print(f"Error: Directory '{MANILA_STORAGE_PATH}' does not exist.")
        return

    # List all files in the Manila storage directory
    files = os.listdir(MANILA_STORAGE_PATH)
    print("Files to organize:", files)

    # Iterate through each file in the directory
    for file in files:
        print(f"Checking file: {file}")
        
        # Check each file against the defined patterns
        for pattern, subfolder in FILE_PATTERNS.items():
            match = re.match(pattern, file)
            if match:
                print(f"Matched pattern '{pattern}' for file '{file}'")

                # Special Case: Handle 'cumulative_activity' files
                if 'cumulative_activity' in subfolder:
                    file_date = match.group(0).split('__')[1][:4]  # Extract the year
                else:
                    file_date = match.group(1)  # Standard date extraction (YYYYMMDD)

                # Define the destination folder structure
                date_directory = os.path.join(MANILA_STORAGE_PATH, file_date)
                target_directory = os.path.join(date_directory, subfolder)

                # Create the target folder if it doesn't exist
                os.makedirs(target_directory, exist_ok=True)

                # Define source and destination file paths
                source_path = os.path.join(MANILA_STORAGE_PATH, file)
                target_path = os.path.join(target_directory, file)

                # Move the file to the appropriate folder
                shutil.move(source_path, target_path)
                print(f"Moved {file} → {target_directory}")
                break  # Move to the next file once a match is found

    print("File organization complete.")


if __name__ == "__main__":
    organize_files()

