import os
import shutil
import re

# Define patterns for file types and their corresponding subdirectories
FILE_PATTERNS = {
    r'batdetect2_pipeline_(\d{8})_(\d{6})\.csv': 'batdetect2',
    r'Buzz_Results_(\d{8})_(\d{6})\.csv': 'buzzfindr',
    r'(\d{8})_(\d{6})_selection\.txt': 'frognet',
    r'(\d{8})_(\d{6})_species\.csv': 'frognet',
    r'(\d{8})_(\d{6})\.bat\.results_USA\.csv': 'battybirdnet',
    r'activity_recover-(\d{8})_UBNA_\d{3}\.png': 'activity_plot'
}

# Base directory for the Manila storage
BASE_DIR = "/path/to/manila/storage"

def move_files():
    # Iterate through both the base directory and existing date directories
    for root, _, files in os.walk(BASE_DIR):
        for filename in files:
            file_path = os.path.join(root, filename)

            # Skip files already correctly placed in their subfolders
            if any(subfolder in file_path for subfolder in FILE_PATTERNS.values()):
                continue

            # Check each pattern to determine the correct folder
            for pattern, subfolder in FILE_PATTERNS.items():
                match = re.match(pattern, filename)
                if match:
                    # Extract date from filename or root folder if already in date dir
                    date_str = match.group(1)

                    # Create the date directory if it doesn't exist
                    date_dir = os.path.join(BASE_DIR, date_str)
                    os.makedirs(date_dir, exist_ok=True)

                    # Create the subfolder inside the date directory
                    subfolder_dir = os.path.join(date_dir, subfolder)
                    os.makedirs(subfolder_dir, exist_ok=True)

                    # Move the file to the appropriate folder
                    dest = os.path.join(subfolder_dir, filename)
                    shutil.move(file_path, dest)

                    print(f"Moved {filename} to {dest}")
                    break  # Stop checking patterns once matched

if __name__ == "__main__":
    move_files()


