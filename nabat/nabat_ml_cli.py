"""Simple client to load tensorflow model, read a wav file, create pulse representation, and classify"""
import argparse
import os
import sys
import numpy as np

from PIL import Image

from db import NABat_DB
from prediction.prediction import Prediction
from spectrogram.spectrogram_v2 import Spectrogram

os.chdir(os.path.dirname(os.path.abspath(__file__)))

class Processor():
    def __init__(self, model, directory):
        self.directory = directory

        self.spectrogram = Spectrogram()

        self.predictor = Prediction(model, self.spectrogram.img_height,
                                    self.spectrogram.img_width, self.spectrogram.img_channels)

        self.db = NABat_DB(
            self.directory, class_list=self.predictor.CLASS_NAMES)
        self.species = self.db.query('select * from species;')
        self.species_id_lookup = [''] * 100
        for s in self.species:
            self.species_id_lookup[s.id] = s.species_code


    def process_single_wav(self, file, path):
        print("Processing: {} in path {}".format(file, path))
        spectrogram = Spectrogram()
        d = spectrogram.process_file(file)
        to_predict = ([], [])
        for i, m in enumerate(d.metadata):
            local_pulse_id = "pulse_"+str(m.offset)
            local_pulse_path = path+"/"+local_pulse_id+".png"
            img_obj = spectrogram.make_training_spectrogram(m.window, d.sample_rate)
            img_obj.save(local_pulse_path)
            
            disk_image = Image.open(local_pulse_path)
            img = np.array(disk_image)
            img = img[..., :3].astype('float32')
            img /= 255.0
            disk_image.close()

            to_predict[0].append(img)
            to_predict[1].append(local_pulse_id)

        all_predictions = self.predictor.predict_images(to_predict[0])

        k = 0
        for prediction in all_predictions:
            print("{} max class {}({}), score {}".format(to_predict[1][k], np.argmax(prediction), self.predictor.CLASS_NAMES[np.argmax(prediction)], prediction[np.argmax(prediction)]))
            k = k+1    

def single_run(file, path):
    processor.process_single_wav(file, path)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Process full spectrum acoustics.')

    parser.add_argument('-p, --path', dest='path', type=str, nargs=1, default=[''],
                        help='The directory to use for .wav file processing.')

    parser.add_argument('-f', "--file", help="Path to local file to process")

    parser.add_argument('-m', "--model", help="Name of analysis model", default="m-1")


    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    print('Initializing...')
    args = parser.parse_args()
    processor = Processor(model=args.model, directory=args.path[0])

    print('Processing a single wav file')
    single_run(args.file, args.path[0])
