# Load devtools and install the 'buzzfindr' package from GitHub
remotes::install_github("joelwjameson/buzzfindr")
library(buzzfindr)

# Set the path to your recordings (ensure the path is correct and accessible)
path = "/app/recordings_buzz"
out_file = "csv"

# Now call the function
detected_buzzes <- buzzfindr(path = path, out.file = out_file)

# View the results (print first few rows to check)
print(head(detected_buzzes))

# Optionally, print a message confirming the file has been saved
cat("Results saved to detected_buzzes.csv\n")

# Set source and target directories
source_dir <- "/app/recordings_buzz/"
target_dir <- "/app/output_buzz/"

# List directories in /app/recordings_buzz
subdirs <- list.dirs("/app/recordings_buzz/", full.names = TRUE, recursive = FALSE)

# Check if there are any subdirectories
if (length(subdirs) > 0) {
    # Get the last subdirectory
    last_subdir <- subdirs[length(subdirs)]  # Access the last subdirectory
    
    # Change to the last subdirectory
    setwd(last_subdir)
    
    # List all .csv files in the last subdirectory
    csv_files <- list.files(pattern = "\\.csv$")
    
    if (length(csv_files) > 0) {
        cat("Found the following .csv files:\n")
        print(csv_files)
        
        # Copy each .csv file to the target directory
        for (file in csv_files) {
            file_path <- file.path(last_subdir, file)  # Full path to the .csv file
            target_path <- file.path(target_dir, file)  # Target path in the output directory
            
            file.copy(file_path, target_path)
            cat("Copied:", file, "to", target_dir, "\n")

            # Remove the file from the source directory after copying
            file.remove(file_path)
            cat("Removed:", file, "from", last_subdir, "\n")
        }
    } else {
        cat("No .csv files found in the last subdirectory.\n")
    }
} else {
    cat("No subdirectories found in /app/recordings_buzz/.\n")
}
