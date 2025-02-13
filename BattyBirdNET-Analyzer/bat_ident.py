"""Module to analyze audio samples.
"""
import argparse
import datetime
import json
import operator
import os
import sys
from multiprocessing import Pool, freeze_support
import numpy as np
import audio
import config as cfg
import model
import species
import utils
import subprocess
import pathlib


def load_codes():
    """Loads the eBird codes.
    Returns:
        A dictionary containing the eBird codes.
    """
    with open(cfg.CODES_FILE, "r") as cfile:
        codes = json.load(cfile)
    return codes

def save_result_file(r: dict[str, list], path: str, afile_path: str):
    """Saves the results to the hard drive.
    Args:
        r: The dictionary with {segment: scores}.
        path: The path where the result should be saved.
        afile_path: The path to audio file.
    """
    # Make folder if it doesn't exist
    if os.path.dirname(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)

    # Selection table
    out_string = ""

    if cfg.RESULT_TYPE == "table":
        # Raven selection header
        header = "Selection\tView\tChannel\tBegin Time (s)\tEnd Time (s)\tSpecies Code\tCommon Name\tConfidence\n"
        selection_id = 0
        # Write header
        out_string += header

        # Extract valid predictions for every timestamp
        for timestamp in get_sorted_timestamps(r):
            rstring = ""
            start, end = timestamp.split("-", 1)

            for c in r[timestamp]:
                if c[1] > cfg.MIN_CONFIDENCE and (not cfg.SPECIES_LIST or c[0] in cfg.SPECIES_LIST):
                    selection_id += 1
                    label = cfg.TRANSLATED_LABELS[cfg.LABELS.index(c[0])]
                    rstring += "{}\tSpectrogram 1\t1\t{}\t{}\t{}\t{}\t{:.4f}\n".format(
                        selection_id,
                        start,
                        end,
                        cfg.CODES[c[0]] if c[0] in cfg.CODES else c[0],
                        label.split("_", 1)[-1],
                        c[1],
                    )

            # Write result string to file
            out_string += rstring

    elif cfg.RESULT_TYPE == "audacity":
        # Audacity timeline labels
        for timestamp in get_sorted_timestamps(r):
            rstring = ""

            for c in r[timestamp]:
                if c[1] > cfg.MIN_CONFIDENCE and (not cfg.SPECIES_LIST or c[0] in cfg.SPECIES_LIST):
                    label = cfg.TRANSLATED_LABELS[cfg.LABELS.index(c[0])]
                    rstring += "{}\t{}\t{:.4f}\n".format(timestamp.replace("-", "\t"), label.replace("_", ", "), c[1])

            # Write result string to file
            out_string += rstring

    elif cfg.RESULT_TYPE == "r":
        # Output format for R
        header = ("filepath,start,end,scientific_name,common_name,confidence,lat,lon,week,"
                  "overlap,sensitivity,min_conf,species_list,model")
        out_string += header

        for timestamp in get_sorted_timestamps(r):
            rstring = ""
            start, end = timestamp.split("-", 1)

            for c in r[timestamp]:
                if c[1] > cfg.MIN_CONFIDENCE and (not cfg.SPECIES_LIST or c[0] in cfg.SPECIES_LIST):
                    label = cfg.TRANSLATED_LABELS[cfg.LABELS.index(c[0])]
                    rstring += "\n{},{},{},{},{},{:.4f},{:.4f},{:.4f},{},{},{},{},{},{}".format(
                        afile_path,
                        start,
                        end,
                        label.split("_", 1)[0],
                        label.split("_", 1)[-1],
                        c[1],
                        cfg.LATITUDE,
                        cfg.LONGITUDE,
                        cfg.WEEK,
                        cfg.SIG_OVERLAP,
                        (1.0 - cfg.SIGMOID_SENSITIVITY) + 1.0,
                        cfg.MIN_CONFIDENCE,
                        cfg.SPECIES_LIST_FILE,
                        os.path.basename(cfg.MODEL_PATH),
                    )

            # Write result string to file
            out_string += rstring

    elif cfg.RESULT_TYPE == "kaleidoscope":
        # Output format for kaleidoscope
        header = ("INDIR,FOLDER,IN FILE,OFFSET,DURATION,scientific_name,"
                  "common_name,confidence,lat,lon,week,overlap,sensitivity")
        out_string += header

        folder_path, filename = os.path.split(afile_path)
        parent_folder, folder_name = os.path.split(folder_path)

        for timestamp in get_sorted_timestamps(r):
            rstring = ""
            start, end = timestamp.split("-", 1)

            for c in r[timestamp]:
                if c[1] > cfg.MIN_CONFIDENCE and (not cfg.SPECIES_LIST or c[0] in cfg.SPECIES_LIST):
                    label = cfg.TRANSLATED_LABELS[cfg.LABELS.index(c[0])]
                    rstring += "\n{},{},{},{},{},{},{},{:.4f},{:.4f},{:.4f},{},{},{}".format(
                        parent_folder.rstrip("/"),
                        folder_name,
                        filename,
                        start,
                        float(end) - float(start),
                        label.split("_", 1)[0],
                        label.split("_", 1)[-1],
                        c[1],
                        cfg.LATITUDE,
                        cfg.LONGITUDE,
                        cfg.WEEK,
                        cfg.SIG_OVERLAP,
                        (1.0 - cfg.SIGMOID_SENSITIVITY) + 1.0,
                    )

            # Write result string to file
            out_string += rstring

    else:
        # CSV output file
        header = "Start (s),End (s),Scientific name,Common name,Confidence\n"

        # Write header
        out_string += header

        for timestamp in get_sorted_timestamps(r):
            rstring = ""

            for c in r[timestamp]:
                start, end = timestamp.split("-", 1)

                if c[1] > cfg.MIN_CONFIDENCE and (not cfg.SPECIES_LIST or c[0] in cfg.SPECIES_LIST):
                    label = cfg.TRANSLATED_LABELS[cfg.LABELS.index(c[0])]
                    rstring += "{},{},{},{},{:.4f}\n".format(start, end, label.split("_", 1)[0],
                                                             label.split("_", 1)[-1], c[1])

            # Write result string to file
            out_string += rstring

    # Save as file
    with open(path, "w", encoding="utf-8") as rfile:
        rfile.write(out_string)
    return out_string


def get_sorted_timestamps(results: dict[str, list]):
    """Sorts the results based on the segments.
    Args:
        results: The dictionary with {segment: scores}.
    Returns:
        Returns the sorted list of segments and their scores.
    """
    return sorted(results, key=lambda t: float(t.split("-", 1)[0]))


def get_raw_audio_from_file(fpath: str):
    """Reads an audio file.
    Reads the file and splits the signal into chunks.
    Args:
        fpath: Path to the audio file.
    Returns:
        The signal split into a list of chunks.
    """
    # Open file
    sig, rate = audio.openAudioFile(fpath, cfg.SAMPLE_RATE)

    # Split into raw audio chunks
    chunks = audio.splitSignal(sig, rate, cfg.SIG_LENGTH, cfg.SIG_OVERLAP, cfg.SIG_MINLEN)

    return chunks


def predict(samples):
    """Predicts the classes for the given samples.

    Args:
        samples: Samples to be predicted.

    Returns:
        The prediction scores.
    """
    # Prepare sample and pass through model
    data = np.array(samples, dtype="float32")
    prediction = model.predict(data)

    # Logits or sigmoid activations?
    if cfg.APPLY_SIGMOID:
        prediction = model.flat_sigmoid(np.array(prediction), sensitivity=-cfg.SIGMOID_SENSITIVITY)

    return prediction


def analyze_file(item):
    """Analyzes a file.

    Predicts the scores for the file and saves the results.

    Args:
        item: Tuple containing (file path, config)

    Returns:
        The `True` if the file was analyzed successfully.
    """
    # Get file path and restore cfg
    fpath: str = item[0]
    cfg.set_config(item[1])

    # Start time
    start_time = datetime.datetime.now()

    # Status
    print(f"Analyzing {fpath}", flush=True)

    try:
        # Open audio file and split into 3-second chunks
        chunks = get_raw_audio_from_file(fpath)

    # If no chunks, show error and skip
    except Exception as ex:
        print(f"Error: Cannot open audio file {fpath}", flush=True)
        utils.writeErrorLog(ex)

        return False

    # Process each chunk
    try:
        start, end = 0, cfg.SIG_LENGTH
        results = {}
        samples = []
        timestamps = []

        for chunk_index, chunk in enumerate(chunks):
            # Add to batch
            samples.append(chunk)
            timestamps.append([start, end])

            # Advance start and end
            start += cfg.SIG_LENGTH - cfg.SIG_OVERLAP
            end = start + cfg.SIG_LENGTH

            # Check if batch is full or last chunk
            if len(samples) < cfg.BATCH_SIZE and chunk_index < len(chunks) - 1:
                continue

            # Predict
            prediction = predict(samples)

            # Add to results
            for i in range(len(samples)):
                # Get timestamp
                s_start, s_end = timestamps[i]

                # Get prediction
                pred = prediction[i]

                # Assign scores to labels
                p_labels = zip(cfg.LABELS, pred)

                # Sort by score
                p_sorted = sorted(p_labels, key=operator.itemgetter(1), reverse=True)

                # Store top 5 results and advance indices
                results[str(s_start) + "-" + str(s_end)] = p_sorted

            # Clear batch
            samples = []
            timestamps = []

    except Exception as ex:
        # Write error log
        print(f"Error: Cannot analyze audio file {fpath}.\n", flush=True)
        utils.writeErrorLog(ex)
        return False

    # Save as selection table
    try:
        # We have to check if output path is a file or directory
        if not cfg.OUTPUT_PATH.rsplit(".", 1)[-1].lower() in ["txt", "csv"]:
            rpath = fpath.replace(cfg.INPUT_PATH, "")
            rpath = rpath[1:] if rpath[0] in ["/", "\\"] else rpath

            # Make target directory if it doesn't exist
            rdir = os.path.join(cfg.OUTPUT_PATH, os.path.dirname(rpath))

            os.makedirs(rdir, exist_ok=True)

            if cfg.RESULT_TYPE == "table":
                rtype = "bat.selection.table.txt"
            elif cfg.RESULT_TYPE == "audacity":
                rtype = ".bat.results.txt"
            else:
                rtype = ".bat.results.csv"

            out_string = save_result_file(results, os.path.join(cfg.OUTPUT_PATH, rpath.rsplit(".", 1)[0] + rtype), fpath)
        else:
            out_string = save_result_file(results, cfg.OUTPUT_PATH, fpath)
            # Save as file
        with open(cfg.OUTPUT_PATH + "Results.csv", "a", encoding="utf-8") as rfile:
            postString = out_string.split("\n", 1)[1]
            # rfile.write(fpath.join(postString.splitlines(True)))
            rfile.write("\n"+fpath+"\n")
            rfile.write(postString)

    except Exception as ex:
        # Write error log
        print(f"Error: Cannot save result for {fpath}.\n", flush=True)
        utils.writeErrorLog(ex)
        return False

    delta_time = (datetime.datetime.now() - start_time).total_seconds()
    print("Finished {} in {:.2f} seconds".format(fpath, delta_time), flush=True)
    return True

def set_analysis_location(kHz = 256):

    if args.area not in ["Bavaria",  "South-Wales", "Sweden", "UK", "USA","USA-EAST","USA-WEST"]:
        exit(code="Unknown location option or disabled during classifier improvement.")
    else:
        args.lat = -1
        args.lon = -1
        if args.kHz == 144:
            cfg.SAMPLE_RATE = 144000
            cfg.SIG_LENGTH = 1
            cfg.SIG_OVERLAP = cfg.SIG_LENGTH / 4.0
            cfg.SIG_MINLEN = cfg.SIG_LENGTH / 3.0
        # args.locale = "en"

    if args.area == "Bavaria":
        if args.kHz == 144:
            cfg.CUSTOM_CLASSIFIER = cfg.BAT_CLASSIFIER_LOCATION + "/BattyBirdNET-Bavaria-144kHz.tflite"
            cfg.LABELS_FILE = cfg.BAT_CLASSIFIER_LOCATION + "/BattyBirdNET-Bavaria-144kHz_Labels.txt"
        else:
            cfg.CUSTOM_CLASSIFIER = cfg.BAT_CLASSIFIER_LOCATION + "/BattyBirdNET-Bavaria-256kHz.tflite"
            cfg.LABELS_FILE = cfg.BAT_CLASSIFIER_LOCATION + "/BattyBirdNET-Bavaria-256kHz_Labels.txt"

        cfg.LABELS = utils.readLines(cfg.LABELS_FILE)
        # args.locale = "en"

    elif args.area == "EU":
        if args.kHz == 144:
            cfg.CUSTOM_CLASSIFIER = cfg.BAT_CLASSIFIER_LOCATION + "/BattyBirdNET-EU-144kHz.tflite"
            cfg.LABELS_FILE = cfg.BAT_CLASSIFIER_LOCATION + "/BattyBirdNET-EU-144kHz_Labels.txt"
        else:
            cfg.CUSTOM_CLASSIFIER = cfg.BAT_CLASSIFIER_LOCATION + "/BattyBirdNET-EU-256kHz.tflite"
            cfg.LABELS_FILE = cfg.BAT_CLASSIFIER_LOCATION + "/BattyBirdNET-EU-256kHz_Labels.txt"

        cfg.LABELS = utils.readLines(cfg.LABELS_FILE)

    elif args.area == "Sweden":
        if args.kHz == 144:
            cfg.CUSTOM_CLASSIFIER = cfg.BAT_CLASSIFIER_LOCATION + "/BattyBirdNET-Sweden-144kHz.tflite"
            cfg.LABELS_FILE = cfg.BAT_CLASSIFIER_LOCATION + "/BattyBirdNET-Sweden-144kHz_Labels.txt"
        else:
            cfg.CUSTOM_CLASSIFIER = cfg.BAT_CLASSIFIER_LOCATION + "/BattyBirdNET-Sweden-256kHz.tflite"
            cfg.LABELS_FILE = cfg.BAT_CLASSIFIER_LOCATION + "/BattyBirdNET-Sweden-256kHz_Labels.txt"

        cfg.LABELS = utils.readLines(cfg.LABELS_FILE)
        args.locale = "se"

    elif args.area == "Scotland":
        if args.kHz == 144:
            cfg.CUSTOM_CLASSIFIER = cfg.BAT_CLASSIFIER_LOCATION + "/BattyBirdNET-Scotland-144kHz.tflite"
            cfg.LABELS_FILE = cfg.BAT_CLASSIFIER_LOCATION + "/BattyBirdNET-Scotland-144kHz_Labels.txt"
        else:
            cfg.CUSTOM_CLASSIFIER = cfg.BAT_CLASSIFIER_LOCATION + "/BattyBirdNET-Scotland-256kHz.tflite"
            cfg.LABELS_FILE = cfg.BAT_CLASSIFIER_LOCATION + "/BattyBirdNET-Scotland-256kHz_Labels.txt"

        cfg.LABELS = utils.readLines(cfg.LABELS_FILE)

    elif args.area == "South-Wales":
        if args.kHz == 144:
            cfg.CUSTOM_CLASSIFIER = cfg.BAT_CLASSIFIER_LOCATION + "/BattyBirdNET-SouthWales-144kHz.tflite"
            cfg.LABELS_FILE = cfg.BAT_CLASSIFIER_LOCATION + "/BattyBirdNET-SouthWales-144kHz_Labels.txt"
        else:
            cfg.CUSTOM_CLASSIFIER = cfg.BAT_CLASSIFIER_LOCATION + "/BattyBirdNET-SouthWales-256kHz.tflite"
            cfg.LABELS_FILE = cfg.BAT_CLASSIFIER_LOCATION + "/BattyBirdNET-SouthWales-256kHz_Labels.txt"

        cfg.LABELS = utils.readLines(cfg.LABELS_FILE)
    elif args.area == "UK":
        if args.kHz == 144:
            cfg.CUSTOM_CLASSIFIER = cfg.BAT_CLASSIFIER_LOCATION + "/BattyBirdNET-UK-144kHz.tflite"
            cfg.LABELS_FILE = cfg.BAT_CLASSIFIER_LOCATION + "/BattyBirdNET-UK-144kHz_Labels.txt"
        else:
            cfg.CUSTOM_CLASSIFIER = cfg.BAT_CLASSIFIER_LOCATION + "/BattyBirdNET-UK-256kHz.tflite"
            cfg.LABELS_FILE = cfg.BAT_CLASSIFIER_LOCATION + "/BattyBirdNET-UK-256kHz_Labels.txt"

        cfg.LABELS = utils.readLines(cfg.LABELS_FILE)

    elif args.area == "USA":
        if args.kHz == 144:
            cfg.CUSTOM_CLASSIFIER = cfg.BAT_CLASSIFIER_LOCATION + "/BattyBirdNET-USA-144kHz.tflite"
            cfg.LABELS_FILE = cfg.BAT_CLASSIFIER_LOCATION + "/BattyBirdNET-USA-144kHz_Labels.txt"
        else:
            cfg.CUSTOM_CLASSIFIER = cfg.BAT_CLASSIFIER_LOCATION + "/BattyBirdNET-USA-256kHz.tflite"
            cfg.LABELS_FILE = cfg.BAT_CLASSIFIER_LOCATION + "/BattyBirdNET-USA-256kHz_Labels.txt"

        cfg.LABELS = utils.readLines(cfg.LABELS_FILE)

    elif args.area == "USA-EAST":
        if args.kHz == 144:
            cfg.CUSTOM_CLASSIFIER = cfg.BAT_CLASSIFIER_LOCATION + "/BattyBirdNET-USA-144kHz.tflite"
            cfg.LABELS_FILE = cfg.BAT_CLASSIFIER_LOCATION + "/BattyBirdNET-USA-144kHz_Labels.txt"
        else:
            cfg.CUSTOM_CLASSIFIER = cfg.BAT_CLASSIFIER_LOCATION + "/BattyBirdNET-USA-EAST-256kHz.tflite"
            cfg.LABELS_FILE = cfg.BAT_CLASSIFIER_LOCATION + "/BattyBirdNET-USA-EAST-256kHz_Labels.txt"

        cfg.LABELS = utils.readLines(cfg.LABELS_FILE)

    elif args.area == "USA-WEST":
        if args.kHz == 144:
            cfg.CUSTOM_CLASSIFIER = cfg.BAT_CLASSIFIER_LOCATION + "/BattyBirdNET-USA-144kHz.tflite"
            cfg.LABELS_FILE = cfg.BAT_CLASSIFIER_LOCATION + "/BattyBirdNET-USA-144kHz_Labels.txt"
        else:
            cfg.CUSTOM_CLASSIFIER = cfg.BAT_CLASSIFIER_LOCATION + "/BattyBirdNET-USA-WEST-256kHz.tflite"
            cfg.LABELS_FILE = cfg.BAT_CLASSIFIER_LOCATION + "/BattyBirdNET-USA-WEST-256kHz_Labels.txt"

        cfg.LABELS = utils.readLines(cfg.LABELS_FILE)

    elif args.area == "MarinCounty":
        if args.kHz == 144:
            cfg.CUSTOM_CLASSIFIER = cfg.BAT_CLASSIFIER_LOCATION + "/BattyBirdNET-MarinCounty-144kHz.tflite"
            cfg.LABELS_FILE = cfg.BAT_CLASSIFIER_LOCATION + "/BattyBirdNET-MarinCounty-144kHz_Labels.txt"
        else:
            cfg.CUSTOM_CLASSIFIER = cfg.BAT_CLASSIFIER_LOCATION + "/BattyBirdNET-MarinCounty-144kHz.tflite"
            cfg.LABELS_FILE = cfg.BAT_CLASSIFIER_LOCATION + "/BattyBirdNET-MarinCounty-144kHz_Labels.txt"
            print("Marin County currently only on 144kHz")
        cfg.LABELS = utils.readLines(cfg.LABELS_FILE)

    else:
        cfg.CUSTOM_CLASSIFIER = None

def set_paths():
    # Set paths relative to script path (requested in #3)
    script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    cfg.MODEL_PATH = os.path.join(script_dir, cfg.MODEL_PATH)
    cfg.LABELS_FILE = os.path.join(script_dir, cfg.LABELS_FILE)
    cfg.TRANSLATED_LABELS_PATH = os.path.join(script_dir, cfg.TRANSLATED_LABELS_PATH)
    cfg.MDATA_MODEL_PATH = os.path.join(script_dir, cfg.MDATA_MODEL_PATH)
    cfg.CODES_FILE = os.path.join(script_dir, cfg.CODES_FILE)
    cfg.ERROR_LOG_FILE = os.path.join(script_dir, cfg.ERROR_LOG_FILE)
    cfg.BAT_CLASSIFIER_LOCATION = os.path.join(script_dir, cfg.BAT_CLASSIFIER_LOCATION)
    cfg.INPUT_PATH = args.i
    cfg.OUTPUT_PATH = args.o

def set_custom_classifier():
    if args.classifier is None:
        return
    cfg.CUSTOM_CLASSIFIER = args.classifier  # we treat this as absolute path, so no need to join with dirname
    cfg.LABELS_FILE = args.classifier.replace(".tflite", "_Labels.txt")  # same for labels file
    cfg.LABELS = utils.readLines(cfg.LABELS_FILE)
    args.lat = -1
    args.lon = -1
    # args.locale = "en"

def add_parser_arguments():
    parser.add_argument("--kHz",
                        default="256",
                        help="Sampling rate. Values in ['144', '256']. "
                             "Defaults to 256kHz.")
    parser.add_argument("--area",
                        default="Bavaria",
                        help="Location. Values in ['Bavaria', 'EU', 'UK', 'USA', 'USA-EAST', 'USA-WEST']. "
                             "Defaults to Bavaria.")

    parser.add_argument("--sensitivity",
                        type=float,
                        default=1.0,
                        help="Detection sensitivity; Higher values result in higher sensitivity. "
                             "Values in [0.5, 1.5]. Defaults to 1.0."
                        )
    parser.add_argument("--min_conf",
                        type=float,
                        default=0.7,
                        help="Minimum confidence threshold. Values in [0.01, 0.99]. Defaults to 0.1.")

    parser.add_argument("--overlap",
                        type=float,
                        default=0.0,
                        help="Overlap of prediction segments. Values in [0.0, 2.9]. Defaults to 0.0."
                        )
    parser.add_argument("--rtype",
                        default="csv",
                        help="Specifies output format. Values in ['table', 'audacity', 'r',  'kaleidoscope', 'csv']. "
                             "Defaults to 'csv' (Raven selection table)."
                        )
    parser.add_argument("--threads",
                        type=int,
                        default=4,
                        help="Number of CPU threads.")
    parser.add_argument("--batchsize",
                        type=int,
                        default=1,
                        help="Number of samples to process at the same time. Defaults to 1."
                        )
    parser.add_argument("--sf_thresh",
                        type=float,
                        default=0.03,
                        help="Minimum species occurrence frequency threshold for location filter. "
                        )
    parser.add_argument("--segment",
                        default="off",
                        help="Generate audio files containing the detected segments. "
                        )
    parser.add_argument("--spectrum",
                        default="off",
                        help="Generate mel spectrograms files containing the detected segments. "
                        )
    parser.add_argument("--noisered",
                        default="off",
                        help="Reduce the microphone specific noise in visualized spectrum."
                        "Values in [off, audiomoth, emtouch2, emtouch2-raspi]. Defaults to off."
                        )
    parser.add_argument("--i",
                        default=cfg.INPUT_PATH_SAMPLES,  # "put-your-files-here/",
                        help="Path to input file or folder. If this is a file, --o needs to be a file too.")
    parser.add_argument("--o",
                        default=cfg.OUTPUT_PATH_SAMPLES,
                        help="Path to output file or folder. If this is a file, --i needs to be a file too.")

    parser.add_argument("--classifier",
                        default=None,
                        help="Path to custom trained classifier. Defaults to None. "
                             "If set, --lat, --lon and --locale are ignored."
                        )
    parser.add_argument("--slist",
                        default="",
                        help='Path to species list file or folder. If folder is provided, species list needs to be '
                             'named "species_list.txt". If lat and lon are provided, this list will be ignored.'
                        )
    parser.add_argument("--lat",
                        type=float,
                        default=-1,
                        help="DISABLED. Set -1 to ignore.")
    parser.add_argument("--lon",
                        type=float,
                        default=-1,
                        help="DISABLED.  Set -1 to ignore.")
    parser.add_argument("--week",
                        type=int,
                        default=-1,
                        help="DISABLED. Set -1 for year-round species list."
                        )
    parser.add_argument("--locale",
                        default="en",
                        help="DISABLED. Defaults to 'en'."
                        )

def load_ebird_codes():
    cfg.CODES = load_codes()
    cfg.LABELS = utils.readLines(cfg.LABELS_FILE)

def load_species_list():
    cfg.LATITUDE, cfg.LONGITUDE, cfg.WEEK = args.lat, args.lon, args.week
    cfg.LOCATION_FILTER_THRESHOLD = max(0.01, min(0.99, float(args.sf_thresh)))
    script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))

    if cfg.LATITUDE == -1 and cfg.LONGITUDE == -1:
        if not args.slist:
            cfg.SPECIES_LIST_FILE = None
        else:
            cfg.SPECIES_LIST_FILE = os.path.join(script_dir, args.slist)

            if os.path.isdir(cfg.SPECIES_LIST_FILE):
                cfg.SPECIES_LIST_FILE = os.path.join(cfg.SPECIES_LIST_FILE, "species_list.txt")

        cfg.SPECIES_LIST = utils.readLines(cfg.SPECIES_LIST_FILE)
    else:
        cfg.SPECIES_LIST_FILE = None
        cfg.SPECIES_LIST = species.getSpeciesList(cfg.LATITUDE, cfg.LONGITUDE, cfg.WEEK, cfg.LOCATION_FILTER_THRESHOLD)
    if not cfg.SPECIES_LIST:
        print(f"Species list contains {len(cfg.LABELS)} species")
    else:
        print(f"Species list contains {len(cfg.SPECIES_LIST)} species")

def parse_input_files():
    if os.path.isdir(cfg.INPUT_PATH):
        cfg.FILE_LIST = utils.collect_audio_files(cfg.INPUT_PATH)
        print(f"Found {len(cfg.FILE_LIST)} files to analyze")
    else:
        cfg.FILE_LIST = [cfg.INPUT_PATH]

def set_analysis_parameters():
    cfg.MIN_CONFIDENCE = max(0.01, min(0.99, float(args.min_conf)))
    cfg.SIGMOID_SENSITIVITY = max(0.5, min(1.0 - (float(args.sensitivity) - 1.0), 1.5))
    cfg.SIG_OVERLAP = max(0.0, min(2.9, float(args.overlap)))
    cfg.BATCH_SIZE = max(1, int(args.batchsize))

def set_hardware_parameters():
    if os.path.isdir(cfg.INPUT_PATH):
        cfg.CPU_THREADS = max(1, int(args.threads))
        cfg.TFLITE_THREADS = 1
    else:
        cfg.CPU_THREADS = 1
        cfg.TFLITE_THREADS = max(1, int(args.threads))

def load_translated_labels():
    cfg.TRANSLATED_LABELS_PATH = cfg.TRANSLATED_BAT_LABELS_PATH
    lfile = os.path.join(cfg.TRANSLATED_LABELS_PATH,
                         os.path.basename(cfg.LABELS_FILE).replace(".txt", "_{}.txt".format(args.locale))
                         )
    if args.locale not in ["en"] and os.path.isfile(lfile):
        cfg.TRANSLATED_LABELS = utils.readLines(lfile)
    else:
        cfg.TRANSLATED_LABELS = cfg.LABELS

def check_result_type():
    cfg.RESULT_TYPE = args.rtype.lower()
    if cfg.RESULT_TYPE not in ["table", "audacity", "r", "kaleidoscope", "csv"]:
        cfg.RESULT_TYPE = "csv"
        print("Unknown output option. Using csv output.")

if __name__ == "__main__":
    freeze_support()  # Freeze support for executable
    parser = argparse.ArgumentParser(description="Analyze audio files with BattyBirdNET")
    add_parser_arguments()
    args = parser.parse_args()
    set_paths()
    load_ebird_codes()
    set_custom_classifier()
    check_result_type()
    set_analysis_location(args.kHz)
    load_translated_labels()
    load_species_list()
    parse_input_files()
    set_analysis_parameters()
    set_hardware_parameters()
    # Add config items to each file list entry.
    # We have to do this for Windows which does not
    # support fork() and thus each process has to
    # have its own config. USE LINUX!
    flist = [(f, cfg.get_config()) for f in cfg.FILE_LIST]

    # Analyze files
    if cfg.CPU_THREADS < 2:
        for entry in flist:
            analyze_file(entry)
    else:
        with Pool(cfg.CPU_THREADS) as p:
            p.map(analyze_file, flist)

    if args.segment == "on" or args.spectrum == "on":
        script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        results_dir = pathlib.Path(os.path.join(script_dir, args.o))
        audio_dir = pathlib.Path(os.path.join(script_dir, args.i ))
        out_dir = pathlib.Path(os.path.join(script_dir, args.i + "/results"))

        cmd = ['python3', "segments.py", "--audio", audio_dir ,"--o", out_dir,"--results", results_dir]
        subprocess.run(cmd)

        if args.spectrum == "on":
            # iterate through the segements folder subfolders, call the plotter
            print("Spectrums in progress ...")
            root_dir = results_dir

            for dir_name in os.listdir(root_dir):
                f = os.path.join(root_dir, dir_name)
                if not os.path.isfile(f):

                    print("Spectrum in progres for: " + f)
                    cmd = ['python3', "batchspec.py", f, f, args.noisered, script_dir]
                    subprocess.run(cmd)
