import os
import sys
import json

# Define the directory containing the filelist files and rclone mount directory
metadata_dir = './osn_bucket_metadata/'
#rclone_mount_dir = '../tmp/osn_bucket/'  # The directory where your rclone mount is located
rclone_mount_dir = '/recordings_2023/'

# Directories and corresponding filelist files
directories = ['ubna_data_01', 'ubna_data_02']#, 'ubna_data_03', 'ubna_data_04']
filelist_files = ['ubna01_wav_files.txt', 'ubna02_wav_files.txt', 'ubna03_wav_files.txt', 'ubna04_wav_files.txt']

# Function to read file list from a file
def read_filelist(file_list_path):
    with open(file_list_path, "r") as f:
        return set(f.read().splitlines())

# Function to get the list of files in the specified directory
'''
def get_files_from_rclone(directory):
    return set(os.path.relpath(os.path.join(root, file), directory)
               for root, _, files in os.walk(directory)
               for file in files)
'''

def get_files_from_rclone(directory):
    current_files = set()
    
    directory_path = os.path.join(rclone_mount_dir, directory)
    dir_path = '.' + directory_path
   
    for root, _, files in os.walk(dir_path):
        for file in files:
            current_files.add(os.path.relpath(os.path.join(root, file), dir_path))
            
    return current_files

# Function to check for new files in each directory
def check_for_new_files():
    new_files = []

    # Iterate over each directory and corresponding filelist
    for dir_name, filelist_name in zip(directories, filelist_files):
        file_path = os.path.join(metadata_dir, filelist_name)
        existing_files = read_filelist(file_path)
        
        # Get the current files in the corresponding directory from the rclone mount
        current_files = get_files_from_rclone(dir_name)
        
        # Find new files (i.e., files in current_files but not in existing_files)
        new_files_in_current = list(current_files - existing_files)

        if new_files_in_current:
            new_files.extend(new_files_in_current)
        

    return new_files

# Run the check
if __name__ == "__main__":

    new_files = check_for_new_files()

    # If new files are found, return success (exit code 0) and print the new files as JSON
    if new_files:
        print("New files detected:")
        new_directories = list(set(os.path.dirname(file) for file in new_files))
        full_directories = [os.path.join(rclone_mount_dir, directory) for directory in new_directories]

        print(new_files)
        print(full_directories)

        with open("new_directories.txt", "w") as f:
            for directory in full_directories:
                f.write(f".{directory}\n")
        sys.exit(0)

    else:
        print("No new files detected.")
        sys.exit(1)  # Failure

