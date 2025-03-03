from pathlib import Path
import csv
from birdnetlib.analyzer import Analyzer
from birdnetlib import Recording
from datetime import datetime

# Set directory containing .wav files
audio_folder = Path("/Users/lawrie/Documents/EcoAcousticAI/NABAT/nabat-ml/examples")

# Set separate output directory for results
output_folder = Path("/Users/lawrie/Documents/EcoAcousticAI/NABAT/nabat-ml/results")
output_folder.mkdir(parents=True, exist_ok=True)  # Ensure output folder exists

# Confidence threshold
CONFIDENCE_THRESHOLD = 0.25

# Maximum consecutive detections to merge for the same species
MAX_CONSECUTIVE = 10

# Latitude and Longitude for filtering (UBNA coordinates) 
LATITUDE = 47.6536          # including this filter is a workaround for filter for ONLY BIRDS
LONGITUDE = -122.2936       # it filters via eBIRD taxonomy files

# Initialize BirdNET-Analyzer model
model = Analyzer()

# RavenPro Selection Table Header
RAVEN_HEADER = "Selection\tView\tChannel\tBegin Time (s)\tEnd Time (s)\tLow Freq (Hz)\tHigh Freq (Hz)\tCommon Name\tScientific Name\tConfidence\tFile\n"

# Process each .wav file in the folder
for audio_file in sorted(audio_folder.glob("*.wav")):
    print(f"\n Processing: {audio_file.name}")

    # Create a Recording object with lat/lon filtering
    recording = Recording(
        model,
        str(audio_file),
        lat=LATITUDE,
        lon=LONGITUDE,
        min_conf=CONFIDENCE_THRESHOLD  # Minimum confidence threshold
    )

    # Analyze the recording
    recording.analyze()

    # Check if there are any detections
    if not recording.detections:
        print(f"No species detected in {audio_file.name}, skipping file creation.")
        continue

    # Define output CSV and RavenPro files in the results folder
    csv_output_file = output_folder / f"{audio_file.stem}_species.csv"
    raven_output_file = output_folder / f"{audio_file.stem}_selection.txt"

    # Merge consecutive detections of the same species
    combined_detections = []
    last_species = None
    last_scientific = None
    last_start = None
    last_end = None
    last_confidences = []
    count = 0

    for detection in recording.detections:
        species = detection["common_name"]
        scientific_name = detection["scientific_name"]
        start_time = detection["start_time"]
        end_time = detection["end_time"]
        confidence = detection["confidence"]

        if species == last_species and count < MAX_CONSECUTIVE:
            # Extend the end time & accumulate confidence
            last_end = end_time
            last_confidences.append(confidence)
            count += 1
        else:
            if last_species is not None:
                # Save previous detection before resetting
                avg_conf = sum(last_confidences) / len(last_confidences)
                combined_detections.append([
                    audio_file.name, last_start, last_end, last_species, last_scientific, avg_conf
                ])

            # Reset for new species detection
            last_species = species
            last_scientific = scientific_name
            last_start = start_time
            last_end = end_time
            last_confidences = [confidence]
            count = 1

    # Save the last accumulated detection
    if last_species is not None:
        avg_conf = sum(last_confidences) / len(last_confidences)
        combined_detections.append([
            audio_file.name, last_start, last_end, last_species, last_scientific, avg_conf
        ])

    # Save predictions in a separate CSV file
    with open(csv_output_file, mode="w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["File Name", "Start Time", "End Time", "Common Name", "Scientific Name", "Confidence"])
        for row in combined_detections:
            writer.writerow(row)

    print(f"Results saved to: {csv_output_file}")

    # Save predictions in RavenPro Selection Table format
    with open(raven_output_file, mode="w", newline="") as ravenfile:
        ravenfile.write(RAVEN_HEADER)
        selection_id = 1  # Selection numbering for RavenPro

        for row in combined_detections:
            file_name, start, end, common_name, scientific_name, confidence = row
            low_freq = 100  # Placeholder (modify based on dataset)
            high_freq = 12000  # Placeholder (modify based on dataset)
            ravenfile.write(
                f"{selection_id}\tSpectrogram 1\t1\t{start}\t{end}\t{low_freq}\t{high_freq}\t{common_name}\t{scientific_name}\t{confidence:.4f}\t{file_name}\n"
            )
            selection_id += 1

    print(f"RavenPro selection table saved to: {raven_output_file}")

print("\n All audio files processed!")