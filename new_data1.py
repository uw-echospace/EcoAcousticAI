import os
import sys
import json

'''
Implementation:
Each file in the osn_bucket_metadata directory contains the relative paths for all files in that directory. 
The files are split up my SD card, so ubna01_wav_files.txt contains all the relative filepaths for files within 
the ubna01 folder. These file paths are the files that have already been "seen" and represent the current state 
of the data. For each SD card, this script compares the files in the metadata with those 
currently existing in the OSN bucket which have been mounted to /tmp/osn_bucket/<SD card #>.
If there are files in the OSN_bucket that are not present in the metadata file, we know new data has been added to 
the bucket. The absolute path of the directory containing the new data is written to new_directories.txt.
Each directory in new_directories.txt is later used as input for the models.
The newly detected files are updated in the metadata files as they have now been seen and 
no longer new. 
If no new data isdetected, the model errors out sys.exit(1).
'''

# Define the directory containing the filelist files and rclone mount directory
metadata_dir = './osn_bucket_metadata/'
rclone_mount_dir = '/tmp/osn_bucket/'  # The directory where your rclone mount is located

# Directories and corresponding filelist files
directories = ['ubna_data_01', 'ubna_data_02', 'ubna_data_03', 'ubna_data_04', 'ubna_data_05']
filelist_files = ['ubna01_wav_files.txt', 'ubna02_wav_files.txt', 'ubna03_wav_files.txt', 'gubna04_wav_files.txt', 'ubna05_wav_files.txt']

# Function to read metadata file from a path
def read_filelist(file_list_path):
    '''
    Parameters
    ------------
    file_list_path : str
        - The path to the metadata file containing existing files in OSN bucket

    Returns
    ------------
    set of existing files that have been seen
    '''
    with open(file_list_path, "r") as f:
        return set(f.read().splitlines())


def get_files_from_rclone(directory):
    '''
    Parameters
    ------------
    directory : str
        - The SD card directory to get a set of the current files in the OSN bucket

    Returns
    ------------
    set of current files in OSN Bucket
    '''
    current_files = set()
    
    directory_path = os.path.join(rclone_mount_dir, directory)
    dir_path = directory_path + '/'
    
    for root, _, files in os.walk(dir_path):
        for file in files:
            full_path = os.path.join(root, file)
            cleaned_path = full_path.replace(dir_path, '')  # Clean path to make it relative to the mounted directory
            current_files.add(cleaned_path)
    
    return current_files

# Function to check for new files in each directory
def check_for_new_files():
    '''
    Function to check for files that exist in OSN bucket but not in list of seen files. 
    Parameters
    ------------
    None

    Returns
    ------------
    list of new files
    '''
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
            for file in new_files_in_current:
                if file.endswith(".WAV") or file.endswith(".wav"):
                    # Full path including the base directory
                    full_path = os.path.join(rclone_mount_dir, dir_name, file)
                    new_files.append(full_path)

                    # Write the new file to the filelist
                    with open(file_path, "a") as f:
                        if not file.endswith('\n'):
                            f.write(f"{file}\n")
                        else:
                            f.write(file)
    
    return new_files

# Run the check
if __name__ == "__main__":
    new_files = check_for_new_files()

    # If new files are found, return success (exit code 0) and print the new files as JSON
    if new_files:
        print("New files detected:", new_files)

        # Create the list of full directory paths
        new_directories = list(set(os.path.dirname(file) for file in new_files))
        abs_path = '/home/ubuntu/' 
        full_directories = [os.path.join(rclone_mount_dir, directory) for directory in new_directories]
        
        # Write the full paths to new_directories.txt
        with open("new_directories.txt", "w") as f:
            for directory in full_directories:
                f.write(f"{directory}\n")
        
        sys.exit(0)  # Success

    else:
        print("No new files detected.")
        sys.exit(1)  # Failure
