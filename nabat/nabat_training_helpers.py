"""Helper functions refactored from notebooks for code reuse and testing"""
import gc
import glob

import matplotlib.pyplot as plt
import multiprocessing as mp
import numpy as np
import pprint
import random

from functools import partial
from pathlib import Path

from db import NABat_DB
from spectrogram.spectrogram_v2 import Spectrogram

def test_db():
    # Test we have a valid database and enumerate the species represented.
    db = NABat_DB()
    species_ids = db.query(' select * from species;')
    pprint.pprint(species_ids)
    db.conn.close()
    return species_ids

# Given a species code, return a numeric id.
def get_manual_id(species_ids, species_code):
    for s in species_ids:
        if s.species_code == species_code:
            return s.id
        
def serial_species(species_ids):
    codes = {}
    for s in species_ids:
        codes[s.species_code] = s.id
    return codes

def serial_species_decoder(species_code, codemap):
    return codemap[species_code]
        
def visualize_input_data(species_ids, directory):
    plt.close(fig='all')
    class_names = []
    wav_count = []
    for s in species_ids:
        class_names.append(s[1])
        wav_count.append(len(glob.glob('{}/{}/*.wav'.format(directory,s[1]), recursive=True)))

    figure = plt.figure(figsize=(40, 10))

    labels = class_names
    count = np.array(wav_count)
    print('Median files per class: ', np.median(count)//1)

    width = 0.35 # the width of the bars: can also be len(x) sequence

    plt.bar(labels, count, width, color="#4a2eff", label='.wav Files')

    plt.ylabel('Count Files')
    plt.xlabel('NABat Species Code')

    plt.title('Count of .wav Files per Species Code')
    plt.legend()
    plt.show()


# This method is meant to be called in parallel and will take a single file path
# and produce a spectrogram for each bat pulse detected within the recording.
def process_file(file_name, species_code_map, create_spectrogram_location):
    
    # Randomly and proprotionally assign files to the train, validate, and test sets.
    # 80% train, 10% validate, 10% test
    draw = None
    r = random.random()
    if r < 0.80:
        draw = 'train'
    elif r < 0.90:
        draw = 'test'
    else:
        draw = 'validate'
      
    # Open a new database connection.
    db = NABat_DB()
    
    # Get metadata about the recording from the file name. The expected naming convention is:
    # p_{nabat_project_id}_g{nabat_grts_id}_f{nabat_file_id}.wav
    # Example: "p163_g89522_f28390444.wav"
    
    species_chunk = file_name.split('/')[-2]
    manual_id = serial_species_decoder(species_chunk, species_code_map)
    grts_id = file_name.split('_')[1][1:]
    file_name_base = file_name.split('/')[-1].replace('.wav','')

    # Process file and return pulse metadata.
    spectrogram = Spectrogram()
    d = spectrogram.process_file(file_name)

    # Add the file to the database.
    file_id, draw = db.add_training_file(d.name, d.duration, d.sample_rate, manual_id, grts_id, draw=draw)

    # For each pulse within file...
    for i, m in enumerate(d.metadata):
        # ...create a place to put the spectrogram.
        path = '{}/{}/{}/t_{}.png'.format(create_spectrogram_location, species_chunk, file_name_base, m.offset)
        Path('{}/{}/{}'.format(create_spectrogram_location, species_chunk, file_name_base)).mkdir(parents=True, exist_ok=True)
        
        # Add the pulse to the database.
        pulse_id = db.add_training_pulse(file_id, m.frequency,
                                  m.amplitude, 0, m.offset, m.time, None, path)
        # On success...
        if pulse_id:
            # ...create a spectrogram image surrounding the pulse and save to disk.
            img = spectrogram.make_training_spectrogram(m.window, d.sample_rate)
            img.save(path)
            img.close()
            
    # Close the database connection.
    db.conn.close()

def generate_spectrograms(species_ids, directory, create_spectrogram_location):
    # Use as many threads as we can, leaving one available to keep notebook responsive.
    thread_count = (mp.cpu_count() - 1)
    print('using {} threads'.format(thread_count))
 
    # Gather wav files.
    files = glob.glob('{}/**/*.wav'.format(directory), recursive=True)
    progress = int(len(files) * 0.01)

    species_code_map = serial_species(species_ids)

    # Start the creation process in parallel and report progress.
    for i in range(0,len(files),progress):
        with mp.Pool(thread_count) as p:
            p.map(partial(process_file, species_code_map=species_code_map, 
                          create_spectrogram_location=create_spectrogram_location), files[i:i+progress])
            gc.collect()
            print('{}%'.format(int(i/progress)))