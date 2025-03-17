import os
import requests
import pandas as pd
from tqdm import tqdm
from urllib.parse import urlparse

# Define input CSV file and output folder
CSV_FILE = "observations-531947.csv"  # Make sure the file exists in the same directory
OUTPUT_FOLDER = "frog_calls/American_Bullfrog_(Invasive)"

# Ensure the output directory exists
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Read the CSV file
print(f"📂 Reading {CSV_FILE}...")
df = pd.read_csv(CSV_FILE)

# Ensure required columns exist
required_columns = {"taxon_id", "id", "scientific_name", "sound_url"}
if not required_columns.issubset(df.columns):
    raise ValueError(f"CSV file is missing required columns: {required_columns - set(df.columns)}")

# Filter rows with valid sound URLs
df = df.dropna(subset=["sound_url"])  # Remove rows where "sound_url" is NaN

def download_audio(observation):
    """Download an audio file from an observation."""
    sound_url = observation["sound_url"]
    if not sound_url.startswith("http"):
        print(f"⚠️ Invalid URL for observation {observation['id']}: {sound_url}")
        return
    
    # Extract file extension from URL
    parsed_url = urlparse(sound_url)
    file_extension = os.path.splitext(parsed_url.path)[1]  # e.g., ".mp3" or ".wav"

    # Extract audio ID from URL
    audio_id = os.path.basename(parsed_url.path).split('.')[0]

    # Construct filename: scientific_name_observationID_audioID.extension
    filename = f"{observation['scientific_name'].replace(' ', '_')}_{observation['id']}_{audio_id}{file_extension}"
    filepath = os.path.join(OUTPUT_FOLDER, filename)

    # Skip if file already exists
    if os.path.exists(filepath):
        print(f"✅ Already downloaded: {filename}")
        return

    try:
        # Download audio file
        response = requests.get(sound_url, stream=True)
        response.raise_for_status()

        # Save file
        with open(filepath, "wb") as file:
            for chunk in response.iter_content(chunk_size=1024):
                file.write(chunk)

        print(f"📥 Downloaded: {filename}")
    
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to download {sound_url}: {e}")

# Iterate through the observations and download audio files
print("🔽 Downloading frog calls...")
for _, row in tqdm(df.iterrows(), total=len(df), desc="Downloading"):
    download_audio(row)

print("✅ Download complete! Check the 'frog_calls' folder.")