# Load devtools and install the 'buzzfindr' package from GitHub
remotes::install_github("joelwjameson/buzzfindr")
library(buzzfindr)

# Set the path to your recordings (ensure the path is correct and accessible)
path = "/app/recordings_buzz"

out_file = "csv"

all_files <- list.files(path = path, full.names = TRUE)

for (file in all_files) {

    # Check if the file ends with .WAV (case insensitive)
    if (grepl("\\.wav$", file, ignore.case = TRUE)) {

        # Create the new file name by changing the extension to lowercase .wav
        new_file_name <- file.path(dirname(file), paste0(tools::file_path_sans_ext(basename(file)), ".wav"))

        cat("within first if statment Renaming file:", file, "to", new_file_name, "\n")

        # Only rename if the file ends with .WAV (case-insensitive check) and ensure it's changed to lowercase .wav
        if (tolower(file) != tolower(new_file_name)) {
            cat("Renaming file:", file, "to", new_file_name, "\n")
            file.rename(file, new_file_name)
        }
    } else {
        cat("Skipping file (not .wav or .WAV):", file, "\n")
    }
}

# Now run the detected_buzzes function with the updated file format
detected_buzzes <- buzzfindr(path = path , out.file = out_file)

# save output files (mounted to manila storage)
target_dir <- "/app/output_buzz/"

# list sub directories 
subdirs = list.dirs('/app/recordings_buzz', full.names = TRUE, recursive = FALSE)

# get output csv files from subdirectories starting with Buzz_Results
buzz_result_subdirs <- subdirs[grepl("^Buzz_Results", basename(subdirs))]

# get date from input wav file
first_wav_file <- all_files[grepl("\\.wav$", all_files, ignore.case = TRUE)][1]
date_part <- substr(basename(first_wav_file), 1, 8)

# Check if there are any subdirectories starting with 'Buzz_Results'
if (length(buzz_result_subdirs) > 0) {
    for (subdir in buzz_result_subdirs) {
        # Change to the subdirectory
        setwd(subdir)
        
        # List all .csv files in the subdirectory
        csv_files <- list.files(pattern = "\\.csv$")
        
        if (length(csv_files) > 0) {
            cat("Found the following .csv files in", subdir, ":\n")
            print(csv_files)
            
            # Copy each .csv file to the target directory
            for (file in csv_files) {
                file_path <- file.path(subdir, file)  # Full path to the .csv file

                # Rename the .csv file based on the extracted date part
                new_file_name <- paste0("Buzzfindr-", date_part, ".csv")
                target_path <- file.path(target_dir, new_file_name)  # Target path in the output directory
                
                file.copy(file_path, target_path)
                cat("Copied:", file, "to", target_dir, "\n")

                # Remove the file from the source directory after copying
                file.remove(file_path)
                cat("Removed:", file, "from", subdir, "\n")
            }
        } else {
            cat("No .csv files found in", subdir, ".\n")
        }
    }
} else {
    cat("No subdirectories starting with 'Buzz_Results' found.\n")
}