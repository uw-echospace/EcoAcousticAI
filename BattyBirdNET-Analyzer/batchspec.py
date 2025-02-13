# under MIT License from https://github.com/agsimmons/batchspec/blob/master/batchspec.py,2023
import argparse
import os
import shutil
import sys
import pathlib
import subprocess

LOSSLESS_EXTENSIONS = ['.flac', '.wav']


def _parse_args():
    parser = argparse.ArgumentParser(description='Batch create spectogram images from files in specified directory')
    parser.add_argument('source_directory', help='Location of audio files')
    parser.add_argument('dest_directory', help='Location to output spectrogram images. Defaults to CWD',
                        nargs='?',
                        default=os.getcwd())
    parser.add_argument('noise_prof', help='Reduce microphone noise.')
    parser.add_argument('script_dir', help='Directory from which called.')
    parser.add_argument('--sox_path', help='Path to SoX executable. Will use sox or sox.exe in PATH by default')

    return parser.parse_args()


def _get_sox_path(specified_sox_path):
    sox_path = None
    if specified_sox_path is not None:

        specified_sox_path = pathlib.Path(specified_sox_path)
        if specified_sox_path.is_file():
            sox_path = specified_sox_path
        else:
            print('ERROR: Specified SoX path is not valid')
            sys.exit(1)

    elif os.name == 'posix':
        sox_path = shutil.which('sox')
    elif os.name == 'nt':
        sox_path = shutil.which('sox.exe')

    if sox_path:
        return sox_path
    else:
        print('ERROR: SoX not found in path and not specified')
        sys.exit(1)


def main(source_directory, dest_directory, sox_path, noise_prof='off', script_dir="."):
    source_directory = pathlib.Path(source_directory)
    dest_directory = pathlib.Path(dest_directory)
    noise_prof_p = ""
    level = '0.5'

    if noise_prof == "audiomoth":
        noise_prof_p = pathlib.Path( os.path.join(script_dir, "checkpoints/bats/mic-noise/noise-audiomoth-1-2.prof"))

    if noise_prof == "emtouch2":
        noise_prof_p = pathlib.Path(os.path.join(script_dir, "checkpoints/bats/mic-noise/noise-touch2.prof"))
        level = '0.7'

    if noise_prof == "emtouch2-raspi":
        noise_prof_p = pathlib.Path(os.path.join(script_dir, "checkpoints/bats/mic-noise/noise-raspi-touch2.prof"))
        level = '0.7'


    # Validate paths
    if not source_directory.is_dir():
        print('ERROR: Source directory is not valid')
        sys.exit(1)
    if not dest_directory.is_dir():
        print('ERROR: Destination directory is not valid')
        sys.exit(1)

    audio_files = [file for file in source_directory.glob('*') if file.is_file() and file.suffix.lower() in LOSSLESS_EXTENSIONS]

    for file in audio_files:
        file_output_path = dest_directory / (file.stem + '.png')
        file_output_path_red = dest_directory / (file.stem + '-noise.png')

        print('Processing {}'.format(file.name))
        file_output_path_n = dest_directory / (file.stem + 'noisered' + file.suffix)
        absolute_file_path = file.absolute()

        if noise_prof != "off":
            subprocess.run([sox_path, file.absolute(), file_output_path_n, 'noisered', noise_prof_p , level])
            subprocess.run([sox_path, file_output_path_n, '-n', 'spectrogram', '-o', file_output_path_red, '-X', '1000'])

        subprocess.run([sox_path, file.absolute(), '-n', 'spectrogram', '-o', file_output_path, '-X', '1000'])



    print('DONE')


if __name__ == '__main__':
    args = _parse_args()

    source_directory = pathlib.Path(args.source_directory)
    dest_directory = pathlib.Path(args.dest_directory)
    sox_path = _get_sox_path(args.sox_path)
    noise_prof = args.noise_prof
    script_dir = args.script_dir

    main(source_directory, dest_directory, sox_path, noise_prof, script_dir)