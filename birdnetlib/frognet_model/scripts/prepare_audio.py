import os
import librosa
import soundfile as sf
from pydub import AudioSegment
from tqdm import tqdm

# Define input (raw) and output (processed) directories
INPUT_DIR = "/Users/lawrie/Downloads/frog_calls/No_UBNA_Frog"
OUTPUT_DIR = "/Users/lawrie/Downloads/prepared_frog_calls/No_UBNA_Frog"

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# TARGET AUDIO SETTINGS
TARGET_SAMPLE_RATE = 48000  # Standard for bioacoustics
TARGET_BIT_DEPTH = 16       # 16-bit PCM WAV
TARGET_CHANNELS = 1         # Mono

# Supported audio formats for conversion
FORMATS = {".mp3", ".mpga", ".m4a", ".flac", ".ogg", ".3gp", ".aac", ".adts", ".mp4", ".wav", ".mov", ".avi"}

def convert_audio(input_path, output_path):
    """Convert audio to WAV with standard parameters."""
    audio = AudioSegment.from_file(input_path)
    audio = audio.set_channels(TARGET_CHANNELS).set_frame_rate(TARGET_SAMPLE_RATE)
    audio.export(output_path, format="wav", parameters=["-ac", "1", "-ar", str(TARGET_SAMPLE_RATE)])

def process_directory():
    """Recursively process all audio files in the input directory."""
    for root, _, files in os.walk(INPUT_DIR):  # Recursively traverse directories
        relative_path = os.path.relpath(root, INPUT_DIR)  # Get relative subdir path
        output_subdir = os.path.join(OUTPUT_DIR, relative_path)  # Maintain directory structure
        os.makedirs(output_subdir, exist_ok=True)

        for filename in tqdm(files, desc=f"Processing {relative_path}"):
            input_path = os.path.join(root, filename)
            ext = os.path.splitext(filename)[1].lower()

            if ext not in FORMATS:
                print(f"⚠️ Skipping unknown file: {filename}")
                continue

            output_filename = os.path.splitext(filename)[0] + ".wav"
            output_path = os.path.join(output_subdir, output_filename)

            try:
                if ext != ".wav":
                    # Convert to WAV
                    convert_audio(input_path, output_path)
                else:
                    # Ensure WAV files have correct format
                    y, sr = librosa.load(input_path, sr=TARGET_SAMPLE_RATE, mono=True)
                    sf.write(output_path, y, TARGET_SAMPLE_RATE, subtype=f"PCM_{TARGET_BIT_DEPTH}")

            except Exception as e:
                print(f"Error processing {filename}: {e}")

if __name__ == "__main__":
    process_directory()
    print(f"\n All audio files processed and saved in {OUTPUT_DIR}!")