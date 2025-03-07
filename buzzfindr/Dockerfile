# Use the official R image as a base
FROM rocker/r-ver:4.2.1

# Update and upgrade apt packages
RUN apt-get update && apt-get upgrade -y

# Then proceed to install the necessary system dependencies
RUN apt-get install -y \
    git \
    cmake \
    libgit2-dev \
    gfortran \
    build-essential \
    libcurl4-gnutls-dev \
    libxml2-dev \
    libssl-dev \
    liberror-perl \
    patch \
    less \
    ssh-client \
    libmbedtls-dev \
    libssh2-1-dev \
    libhttp-parser-dev \
    && apt-get clean

# Install necessary R packages
RUN R -e "install.packages(c('nloptr', 'bioacoustics', 'lme4', 'pbkrtest', 'car'))"

# Install necessary R packages
RUN R -e "install.packages(c('seewave', 'tuneR', 'runner', 'svMisc', 'rlist', 'dplyr', 'entropy', 'parallel'), repos = 'https://cran.rstudio.com/')"


RUN R -e "install.packages('remotes', repos = 'https://cran.rstudio.com/')"

# Install 'buzzfindr' from GitHub using devtools
RUN R -e "remotes::install_github('joelwjameson/buzzfindr')"

# Set working directory in the container
WORKDIR /app

# Copy your script and any necessary files into the container
COPY . .

RUN ls -l /app/

RUN mkdir -p /app/output_buzz/

# Set the R script entry point
CMD ["Rscript", "buzzfindr_script.R"]

# Expose port 8787 if you're using RStudio Server or any other service that requires it
EXPOSE 8787
