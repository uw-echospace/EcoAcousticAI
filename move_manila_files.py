import os
import shutil
import re

# Path to Manila storage
MANILA_STORAGE_PATH = "/ecoacoustic-storage"

# Regex patterns for files with date in filename
FILE_PATTERNS = {
    r"batdetect2_pipeline_(\d{8})_\d{6}\.csv": 'batdetect2',
    r"Buzz_Results_(\d{8})_\d{6}\.csv": 'buzzfindr',
    r"activity_recover-(\d{8})_UBNA_\d{3}\.png": 'activity_plot',
    r"frognet_(\d{8})_(\d{6})_selection\.txt": 'frognet',
    r"frognet_(\d{8})_(\d{6})_species\.csv": 'frognet',
    r"(\d{8})_(\d{6})\.bat\.results_USA\.csv": 'battybirdnet',
    r"cumulative_activity__\d{4}_.*\.png": 'cumulative_activity'
}


def organize_files():
    if not os.path.exists(MANILA_STORAGE_PATH):
        print(f"Error: Directory '{MANILA_STORAGE_PATH}' does not exist.")
        return

    files = os.listdir(MANILA_STORAGE_PATH)
    print("Files to organize:", files)

    for file in files:
        for pattern, subfolder in FILE_PATTERNS.items():
            match = re.match(pattern, file)
            if match:
                file_date = match.group(1)  # Extract date from filename (e.g., '20230825')

                # Create the target directory and subdirectory
                date_directory = os.path.join(MANILA_STORAGE_PATH, file_date)
                target_directory = os.path.join(date_directory, subfolder)
                os.makedirs(target_directory, exist_ok=True)
                print(f"Created directory: {target_directory}")

                # Move the file
                source_path = os.path.join(MANILA_STORAGE_PATH, file)
                target_path = os.path.join(target_directory, file)

                shutil.move(source_path, target_path)
                print(f"Moved {file} → {target_directory}")
                break  # Found a match, skip checking the remaining patterns

    print("File organization complete.")

if __name__ == "__main__":
    organize_files()
