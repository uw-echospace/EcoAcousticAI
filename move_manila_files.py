import os
import re
import shutil
from datetime import datetime

# Path to Manila storage
MANILA_STORAGE_PATH = "/ecoacoustic-storage"

# Regex pattern for CSV files with date in filename
FILE_PATTERN = re.compile(r"batdetect2_pipeline_(\d{8})_\d{6}\.csv")

def organize_files():
    if not os.path.exists(MANILA_STORAGE_PATH):
        print(f"Error: Manila storage path '{MANILA_STORAGE_PATH}' not found.")
        return

    # List all files in the Manila storage root
    files = [f for f in os.listdir(MANILA_STORAGE_PATH) if os.path.isfile(os.path.join(MANILA_STORAGE_PATH, f))]
    print(files)

    for file in files:
        match = FILE_PATTERN.match(file)
        if match:
            file_date = match.group(1)  # Extract date from filename (e.g., '20230825')

            # Create the target directory if it doesn't exist
            target_directory = os.path.join(MANILA_STORAGE_PATH, file_date)
            os.makedirs(target_directory, exist_ok=True)
            print(target_directory)

            # Move the file
            source_path = os.path.join(MANILA_STORAGE_PATH, file)
            target_path = os.path.join(target_directory, file)

            shutil.move(source_path, target_path)
            print(f"Moved {file} → {target_directory}")

    print("File organization complete.")

if __name__ == "__main__":
    organize_files()
