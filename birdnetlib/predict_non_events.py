from pathlib import Path
import csv
import concurrent.futures
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

# Load Custom Species List (Modify this path)
custom_species_list_path = Path("/Users/lawrie/Documents/nonevent_list.txt")

# Initialize BirdNET-Analyzer model with the custom species list
model = Analyzer(custom_species_list_path=str(custom_species_list_path))

# Process each .wav file in the folder
for audio_file in sorted(audio_folder.glob("*.wav")):
    print(f"\n Processing: {audio_file.name}")

    # Create a Recording object (without lat/lon filtering to avoid empty results)
    recording = Recording(
        model,
        str(audio_file),
        min_conf=CONFIDENCE_THRESHOLD  # Minimum confidence threshold
    )

    # Analyze the recording
    recording.analyze()

    # Check if detections exist
    if not recording.detections:
        print(f"No species detected in {audio_file.name}, skipping file creation.")
        continue

    # Sort detections: (1) Start time, (2) End time, (3) Confidence (descending)
    sorted_detections = sorted(
        recording.detections, 
        key=lambda d: (d["start_time"], d["end_time"], -d["confidence"])
    )

    # Dictionary to store the most confident detection per (start_time, end_time) interval
    best_detections = {}

    # Merge consecutive detections
    combined_detections = []
    last_species = None
    last_scientific = None
    last_start = None
    last_end = None
    last_confidences = []
    count = 0

    for detection in sorted_detections:
        species = f"{detection['scientific_name']} {detection['common_name']}"
        scientific_name = f"{detection['scientific_name']} {detection['common_name']}"
        start_time = detection["start_time"]
        end_time = detection["end_time"]
        confidence = detection["confidence"]

        # Keep only the most confident species per (start_time, end_time) window
        key = (start_time, end_time)
        if key not in best_detections or confidence > best_detections[key][2]:
            best_detections[key] = (species, scientific_name, confidence)




        # Only process species that match the custom species list
        # if species in custom_species_list:
        if species == last_species and count < MAX_CONSECUTIVE:
            last_end = end_time
            last_confidences.append(confidence)
            count += 1
        else:
            if last_species is not None:
                avg_conf = sum(last_confidences) / len(last_confidences)
                combined_detections.append([audio_file.name, last_start, last_end, last_species, last_scientific, avg_conf])

            last_species = species
            last_scientific = scientific_name
            last_start = start_time
            last_end = end_time
            last_confidences = [confidence]
            count = 1
            
    # Convert dictionary to sorted list
    final_detections = sorted(best_detections.items())
    
    # Save the last accumulated detection
    if last_species is not None:
        avg_conf = sum(last_confidences) / len(last_confidences)
        combined_detections.append([audio_file.name, last_start, last_end, last_species, last_scientific, avg_conf])

    # Define output files
    csv_output_file = output_folder / f"{audio_file.stem}_species.csv"
    raven_output_file = output_folder / f"{audio_file.stem}_selection.txt"
    
    # Save results in CSV format
    with open(csv_output_file, mode="w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["File Name", "Start Time", "End Time", "Common Name", "Scientific Name", "Confidence"])
        for row in combined_detections:
            writer.writerow(row)

    print(f"Results saved to: {csv_output_file}")

    # Save results in RavenPro selection format
    with open(raven_output_file, mode="w", newline="") as ravenfile:
        ravenfile.write("Selection\tView\tChannel\tBegin Time (s)\tEnd Time (s)\tLow Freq (Hz)\tHigh Freq (Hz)\tCommon Name\tScientific Name\tConfidence\tFile\n")
        selection_id = 1

        for row in combined_detections:
            file_name, start, end, common_name, scientific_name, confidence = row
            low_freq = 300
            high_freq = 15000
            ravenfile.write(
                f"{selection_id}\tSpectrogram 1\t1\t{start}\t{end}\t{low_freq}\t{high_freq}\t{common_name}\t{scientific_name}\t{confidence:.4f}\t{file_name}\n"
            )
            selection_id += 1

    print(f"RavenPro selection table saved to: {raven_output_file}")

print("\nAll audio files processed!")