# Check if devtools is installed, if not, install it
if (!require(devtools)) {
  install.packages("devtools")
}

# Load devtools and install the 'buzzfindr' package from GitHub
devtools::install_github("joelwjameson/buzzfindr")
library(buzzfindr)

# Set the path to your recordings (ensure the path is correct and accessible)
path <- "~/recordings_2023"

# Run the detection function from 'buzzfindr'
detected_buzzes <- buzzfindr(path = path)

# View the results (print first few rows to check)
print(head(detected_buzzes))

# Write the detected buzzes dataframe to a CSV file
write.csv(detected_buzzes, "detected_buzzes.csv", row.names = FALSE)

# Optionally, print a message confirming the file has been saved
cat("Results saved to detected_buzzes.csv\n")

