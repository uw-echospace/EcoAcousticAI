# Load devtools and install the 'buzzfindr' package from GitHub
remotes::install_github("joelwjameson/buzzfindr")
library(buzzfindr)

# Set the path to your recordings (ensure the path is correct and accessible)
path = "/app/recordings_buzz"
#path = "/Users/igokhale/EcoAcousticAI/recordings_2023/ubna_data_01/recover-20210604_unit1/UBNA06"
out_file = "csv"

all_files <- list.files(path = path, full.names = TRUE)

# Iterate through the files in the directory
for (file in all_files) {
    # Check if the file ends with .wav or .WAV
    if (grepl("\\.wav$", file, ignore.case = TRUE)) {
        # Convert .WAV to .wav by renaming the file (change extension to lowercase)
        new_file_name <- paste0(tools::file_path_sans_ext(basename(file)), ".wav")
        
        # Only rename if the file ends with .WAV and ensure it's changed to lowercase .wav
        if (tolower(file) != tolower(new_file_name)) {
            file.rename(file, new_file_name)
        }
    } else {
        cat("Skipping file (not .wav or .WAV):", file, "\n")
    }
}

# Now run the detected_buzzes function with the updated file
detected_buzzes <- buzzfindr(path = path , out.file = out_file)

target_dir <- "/app/output_buzz/"

#target_dir = "/Users/igokhale/EcoAcousticAI/test_out"

# List directories in /app/recordings_buzz
#subdirs <- list.dirs("/app/accepted_files/", full.names = TRUE, recursive = FALSE)

subdirs = list.dirs(source_dir, full.names = TRUE, recursive = FALSE)

buzz_result_subdirs <- subdirs[grepl("^Buzz_Results", basename(subdirs))]

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

                new_file_name <- paste0("Buzzfindr-", date_part, ".csv")

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