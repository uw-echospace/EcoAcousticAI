import rpy2.robjects as ro
import rpy2.robjects.packages as rpackages

# Install and load the 'buzzfindr' R package (if not already installed)
if not rpackages.isinstalled('buzzfindr'):
    utils = rpackages.importr('utils')
    utils.install_github('joelwjameson/buzzfindr')

buzzfindr = rpackages.importr('buzzfindr')

# Set the path to your recordings
path = "~/recordings"

# Run the detection function from 'buzzfindr'
detected_buzzes = buzzfindr.buzzfindr(path=path)

from rpy2.robjects import pandas2ri
pandas2ri.activate()

# Convert the R DataFrame to pandas DataFrame
detected_buzzes_df = pandas2ri.rpy2py(detected_buzzes)

# Write the pandas DataFrame to a CSV file
detected_buzzes_df.to_csv('detected_buzzes.csv', index=False)

print("Results saved to detected_buzzes.csv")


