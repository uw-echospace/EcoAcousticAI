import numpy as np
import argparse
import pandas as pd
import dask.dataframe as dd
import soundfile as sf
from tqdm import tqdm

import matplotlib.pyplot as plt
import matplotlib.colors as colors

import datetime as dt
from pathlib import Path
from torch import multiprocessing

import exiftool
import suncalc
from sklearn.cluster import KMeans
import scipy

# set python path to correctly use batdetect2 submodule
import sys
sys.path.append(str(Path.cwd()))
sys.path.append(str(Path.cwd() / "src/models/bat_call_detector/batdetect2/"))

from scfg import get_config
from pipeline import pipeline
from utils.utils import gen_empty_df, convert_df_ravenpro

SEATTLE_LATITUDE = 47.655181
SEATTLE_LONGITUDE = -122.293123


FREQ_GROUPS = {
                'E18 Bridge' : {'': [0, 96000],
                          'LF1_': [13000, 50000],
                          'HF1_': [34000, 74000],
                          'HF2_': [42000, 96000]},
                'Carp Pond' : {'': [0, 96000],
                          'LF1_': [13000, 50000],
                          'HF1_': [34000, 74000],
                          'HF2_': [42000, 96000]},

                'Foliage' : {'': [0, 96000],
                          'LF1_': [13000, 50000],
                          'HF1_': [34000, 74000],
                          'HF2_': [42000, 96000]},

                'Telephone Field' : {'': [0, 96000],
                          'LF1_': [13000, 50000],
                          'HF1_': [30000, 78000],
                          'HF2_': [41000, 102000]},

                'Central Pond' : {'': [0, 96000],
                          'LF1_': [13000, 50000],
                          'HF1_': [34000, 74000],
                          'HF2_': [42000, 96000]}
                }


LABEL_FOR_GROUPS = {
                    0: 'LF', 
                    1: 'HF'
                    }

def generate_segments(audio_file: Path, output_dir: Path, start_time: float, duration: float):
    """
    Segments audio file into clips of duration length and saves them to output/tmp folder.
    Allows detection model to be run on segments instead of entire file as recommended.
    These segments will be deleted from the output/tmp folder after detections have been generated.

    Parameters
    ------------
    audio_file : `pathlib.Path`
        - The path to an audio_file from the input directory provided in the command line
    output_dir : `pathlib.Path`
        - The path to the tmp folder that saves all of our segments.
    start_time : `float`
        - The time at which the segments will start being generated from within the audio file
    duration : `float`
        - The duration of all segments generated from the audio file.

    Returns
    ------------
    output_files : `List`
        - The path (a str) to each generated segment of the given audio file will be stored in this list.
        - The offset of each generated segment of the given audio file will be stored in this list.
        - Both items are stored in a dict{} for each generated segment.
    """
    
    ip_audio = sf.SoundFile(audio_file)

    sampling_rate = ip_audio.samplerate
    # Convert to sampled units
    ip_start = int(start_time * sampling_rate)
    ip_duration = int(duration * sampling_rate)
    ip_end = ip_audio.frames

    output_files = []

    # for the length of the duration, process the audio into duration length clips
    for sub_start in range(ip_start, ip_end, ip_duration):
        sub_end = np.minimum(sub_start + ip_duration, ip_end)

        # For file names, convert back to seconds 
        op_file = audio_file.name.replace(" ", "_")
        start_seconds =  sub_start / sampling_rate
        end_seconds =  sub_end / sampling_rate
        op_file_en = "__{:.2f}".format(start_seconds) + "_" + "{:.2f}".format(end_seconds)
        op_file = op_file[:-4] + op_file_en + ".wav"
        
        op_path = output_dir / op_file
        output_files.append({
            "input_filepath": audio_file,
            "audio_file": op_path, 
            "offset":  start_time + (sub_start/sampling_rate),
        })
        
        if (not(op_path.exists())):
            sub_length = sub_end - sub_start
            ip_audio.seek(sub_start)
            op_audio = ip_audio.read(sub_length)
            sf.write(op_path, op_audio, sampling_rate, subtype='PCM_16')

    return output_files 

def generate_segmented_paths(audio_files, cfg):
    """
    Generates and returns a list of segments using provided cfg parameters for each audio file in audio_files.

    Parameters
    ------------
    audio_files : `List`
        - List of pathlib.Path objects of the paths to each audio file in the provided input directory.
    cfg : `dict`
        - A dictionary of pipeline parameters:
        - tmp_dir is the directory where segments will be stored
        - start_time is the time at which segments are generated from each audio file.
        - segment_duration is the duration of each generated segment

    Returns
    ------------
    segmented_file_paths : `List`
        - A list of dictionaries related to every generated segment.
        - Each dictionary stores a generated segment's path in the tmp_dir and offset in the original audio file.
    """

    segmented_file_paths = []
    for audio_file in audio_files:
        segmented_file_paths += generate_segments(
            audio_file = audio_file, 
            output_dir = cfg['tmp_dir'],
            start_time = cfg['start_time'],
            duration   = cfg['segment_duration'],
        )
    return segmented_file_paths


def initialize_mappings(necessary_paths, cfg):
    """
    Generates and returns a list of mappings using provided cfg parameters for each audio segment in the provided necessary paths.

    Parameters
    ------------
    necessary_paths : `List`
        - List of dictionaries generated by generate_segmented_paths()
    cfg : `dict`
        - A dictionary of pipeline parameters:
        - models is the models in the pipeline that are being used.

    Returns
    ------------
    l_for_mapping : `List`
        - A list of dictionaries related to every generated segment with more pipeline details.
        - Each dictionary stores the prior segmented_path dict{}, the model to apply, and the original file name of the segment.
    """

    l_for_mapping = [{
        'audio_seg': audio_seg, 
        'model': cfg['models'][0],
        'original_file_name': audio_seg["input_filepath"],
        } for audio_seg in necessary_paths]

    return l_for_mapping

def get_section_of_call_in_file(detection, audio_file):
    fs = audio_file.samplerate

    call_dur = (detection['end_time'] - detection['start_time'])
    pad = min(min(detection['start_time'] - call_dur, 1795 - detection['end_time']), 0.006) / 3
    start = detection['start_time'] - call_dur - (3*pad)
    duration = (2 * call_dur) + (4*pad)

    audio_file.seek(int(fs*start))
    audio_seg = audio_file.read(int(fs*duration))

    length_of_section = call_dur + (2*pad)

    return audio_seg, length_of_section

def get_snr_from_band_limited_signal(snr_call_signal, snr_noise_signal): 
    signal_power_rms = np.sqrt(np.square(snr_call_signal).mean())
    noise_power_rms = np.sqrt(np.square(snr_noise_signal).mean())
    snr = abs(20 * np.log10(signal_power_rms / noise_power_rms))
    return snr


def bandpass_audio_signal(audio_seg, fs, low_freq_cutoff, high_freq_cutoff):
    nyq = fs // 2
    low_cutoff = (low_freq_cutoff) / nyq
    high_cutoff =  (high_freq_cutoff) / nyq
    b, a = scipy.signal.butter(4, [low_cutoff, high_cutoff], btype='band', analog=False)
    band_limited_audio_seg = scipy.signal.filtfilt(b, a, audio_seg)

    return band_limited_audio_seg

def compute_welch_psd_of_call(call, fs, audio_info):
    freqs, welch = scipy.signal.welch(call, fs=fs, detrend=False, scaling='spectrum')
    cropped_welch = welch[(freqs<=audio_info['max_freq_visible'])]
    audio_spectrum_mag = np.abs(cropped_welch)
    audio_spectrum_db =  10*np.log10(audio_spectrum_mag)
    normalized_audio_spectrum_db = audio_spectrum_db - audio_spectrum_db.max()

    thresh = -100
    peak_db = np.zeros(len(normalized_audio_spectrum_db))+thresh
    peak_db[normalized_audio_spectrum_db>=thresh] = normalized_audio_spectrum_db[normalized_audio_spectrum_db>=thresh]

    original_freq_vector = np.arange(0, len(peak_db), 1).astype('int')
    common_freq_vector = np.linspace(0, len(peak_db)-1, audio_info['num_points']).astype('int')
    interp_kind = 'linear'
    interpolated_points_from_welch = scipy.interpolate.interp1d(original_freq_vector, peak_db, kind=interp_kind)(common_freq_vector)

    return interpolated_points_from_welch

def gather_features_of_interest(dets, kmean_welch, audio_file):
    fs = audio_file.samplerate
    features_of_interest = dict()
    features_of_interest['call_signals'] = []
    features_of_interest['welch_signals'] = []
    features_of_interest['snrs'] = []
    features_of_interest['peak_freqs'] = []
    features_of_interest['classes'] = []
    nyquist = fs//2
    for index, row in dets.iterrows():
        audio_seg, length_of_section = get_section_of_call_in_file(row, audio_file)
        
        freq_pad = 2000
        low_freq_cutoff = row['low_freq']-freq_pad
        high_freq_cutoff = min(nyquist-1, row['high_freq']+freq_pad)
        band_limited_audio_seg = bandpass_audio_signal(audio_seg, fs, low_freq_cutoff, high_freq_cutoff)

        signal = band_limited_audio_seg.copy()
        signal[:int(fs*(length_of_section))] = 0
        noise = band_limited_audio_seg - signal
        snr_call_signal = signal[-int(fs*length_of_section):]
        snr_noise_signal = noise[:int(fs*length_of_section)]
        features_of_interest['call_signals'].append(snr_call_signal)

        snr = get_snr_from_band_limited_signal(snr_call_signal, snr_noise_signal)
        features_of_interest['snrs'].append(snr)

        welch_info = dict()
        welch_info['num_points'] = 100
        max_visible_frequency = 96000
        welch_info['max_freq_visible'] = max_visible_frequency
        welch_signal = compute_welch_psd_of_call(snr_call_signal, fs, welch_info)
        features_of_interest['welch_signals'].append(welch_signal)

        peaks = np.where(welch_signal==max(welch_signal))[0][0]
        features_of_interest['peak_freqs'].append((max_visible_frequency/len(welch_signal))*peaks)
        
        welch_signal = (welch_signal).reshape(1, len(welch_signal))
        features_of_interest['classes'].append(kmean_welch.predict(welch_signal)[0])

    features_of_interest['call_signals'] = np.array(features_of_interest['call_signals'], dtype='object')

    return features_of_interest

def open_and_get_call_info(audio_file, dets):
    welch_key = 'all_locations'
    output_dir = Path(f'{Path(__file__).parent}/../../duty-cycle-investigation/data/generated_welch/{welch_key}')
    output_file_type = 'top1_inbouts_welch_signals'
    #welch_data = pd.read_csv(output_dir / f'2022_{welch_key}_{output_file_type}.csv', index_col=0, low_memory=False)
    welch_data = pd.read_csv('/app/bat-detect-msds/2022_all_locations_top1_inbouts_welch_signals.csv', index_col = 0, low_memory = False)
    
    k = 2
    kmean_welch = KMeans(n_clusters=k, n_init=10, random_state=1).fit(welch_data.values)

    features_of_interest = gather_features_of_interest(dets, kmean_welch, audio_file)

    dets.reset_index(drop=True, inplace=True)

    dets['sampling_rate'] = len(dets) * [audio_file.samplerate]
    dets.insert(0, 'SNR', features_of_interest['snrs'])
    dets.insert(0, 'peak_frequency', features_of_interest['peak_freqs'])
    dets.insert(0, 'KMEANS_CLASSES', pd.Series(features_of_interest['classes']).map(LABEL_FOR_GROUPS))

    return features_of_interest['call_signals'], dets

def classify_calls_from_file(bd2_predictions, data_params):
    file_path = Path(data_params['audio_file'])
    audio_file = sf.SoundFile(file_path)
    call_signals, dets = open_and_get_call_info(audio_file, bd2_predictions.copy())
    return dets

def run_models(file_mappings):
    """
    Runs the batdetect2 model to detect bat search-phase calls in the provided audio segments and saves detections into a .csv.

    Parameters
    ------------
    file_mappings : `List`
        - List of dictionaries generated by initialize_mappings()

    Returns
    ------------
    bd_dets : `pandas.DataFrame`
        - A DataFrame of detections that will also be saved in the provided output_dir under the above csv_name
        - 7 columns in this DataFrame: start_time, end_time, low_freq, high_freq, detection_confidence, event, input_file
        - Detections are always specified w.r.t their input_file; earliest start_time can be 0 and latest end_time can be 1795.
        - Events are always "Echolocation" as we are using a model that only detects search-phase calls.
    """

    bd_dets = pd.DataFrame()
    for i in tqdm(range(len(file_mappings))):
        cur_seg = file_mappings[i]
        bd_annotations_df = cur_seg['model']._run_batdetect(cur_seg['audio_seg']['audio_file'])
        bd_preds_classed = classify_calls_from_file(bd_annotations_df, cur_seg['audio_seg'])
        bd_offsetted = pipeline._correct_annotation_offsets(
                bd_preds_classed,
                cur_seg['original_file_name'],
                cur_seg['audio_seg']['offset']
            )
        bd_dets = pd.concat([bd_dets, bd_offsetted])

    median_peak_HF_freq = bd_dets[bd_dets['KMEANS_CLASSES']=='HF']['peak_frequency'].median()
    median_peak_LF_freq = bd_dets[bd_dets['KMEANS_CLASSES']=='LF']['peak_frequency'].median()
    print(f'Median LF frequency in File: {median_peak_LF_freq}')
    print(f'Median HF frequency in File: {median_peak_HF_freq}')
    lf_inds = (bd_dets['peak_frequency']<median_peak_LF_freq+7000)&(bd_dets['peak_frequency']>median_peak_LF_freq-7000)
    hf_inds = (bd_dets['peak_frequency']>median_peak_HF_freq-7000)

    lf_dets = bd_dets[lf_inds&(bd_dets['KMEANS_CLASSES']=='LF')]
    hf_dets = bd_dets[hf_inds&(bd_dets['KMEANS_CLASSES']=='HF')]

    all_dets = pd.concat([hf_dets, lf_dets]).sort_index()
    return all_dets

def apply_models(file_path_mappings, cfg):
    """
    Runs the batdetect2 model to detect bat search-phase calls in the provided audio segments and saves detections into a dataframe

    Parameters
    ------------
    file_mappings : `List`
        - List of dictionaries generated by initialize_mappings()
    cfg : `dict`
        - A dictionary of pipeline parameters:
        - models is the models in the pipeline that are being used.

    Returns
    ------------
    bd_preds : `pandas.DataFrame`
        - A DataFrame of detections that will also be saved in the provided output_dir under the above csv_name
        - 7 columns in this DataFrame: start_time, end_time, low_freq, high_freq, detection_confidence, event, input_file
        - Detections are always specified w.r.t their input_file; earliest start_time can be 0 and latest end_time can be 1795.
        - Events are always "Echolocation" as we are using a model that only detects search-phase calls.
    """

    process_pool = multiprocessing.Pool(cfg['num_processes'])

    bd_dets = tqdm(
            process_pool.imap(apply_model, file_path_mappings, chunksize=1), 
            desc=f"Applying BatDetect2",
            total=len(file_path_mappings),
        )
    
    bd_preds = gen_empty_df() 
    bd_preds = pd.concat(bd_dets, ignore_index=True)

    median_peak_HF_freq = bd_preds[bd_preds['KMEANS_CLASSES']=='HF']['peak_frequency'].median()
    median_peak_LF_freq = bd_preds[bd_preds['KMEANS_CLASSES']=='LF']['peak_frequency'].median()
    print(f'Median LF frequency in File: {median_peak_LF_freq}')
    print(f'Median HF frequency in File: {median_peak_HF_freq}')
    lf_inds = (bd_preds['peak_frequency']<median_peak_LF_freq+7000)&(bd_preds['peak_frequency']>median_peak_LF_freq-7000)
    hf_inds = (bd_preds['peak_frequency']>median_peak_HF_freq-7000)

    lf_dets = bd_preds[lf_inds&(bd_preds['KMEANS_CLASSES']=='LF')]
    hf_dets = bd_preds[hf_inds&(bd_preds['KMEANS_CLASSES']=='HF')]

    all_dets = pd.concat([hf_dets, lf_dets]).sort_index()
    return all_dets

def apply_model(file_mapping):
    """
    Runs the batdetect2 model on a single provided audio segmens and corrects the offsets according the segment.

    Parameters
    ------------
    file_mappings : `List`
        - List of dictionaries generated by initialize_mappings()

    Returns
    ------------
    corrected_bd_dets : `pandas.DataFrame`
        - A DataFrame of detections that will also be saved in the provided output_dir under the above csv_name
        - 7 columns in this DataFrame: start_time, end_time, low_freq, high_freq, detection_confidence, event, input_file
        - Detections are always specified w.r.t their input_file; earliest start_time can be 0 and latest end_time can be 1795.
        - Events are always "Echolocation" as we are using a model that only detects search-phase calls.
    """

    bd_dets = file_mapping['model']._run_batdetect(file_mapping['audio_seg']['audio_file'])
    bd_preds_classed = classify_calls_from_file(bd_dets, file_mapping['audio_seg'])
    corrected_bd_dets = pipeline._correct_annotation_offsets(
                                                            bd_preds_classed,
                                                            file_mapping['original_file_name'],
                                                            file_mapping['audio_seg']['offset']
                                                            )

    return corrected_bd_dets

def _save_predictions(annotation_df, output_dir, cfg):
    """
    Saves a dataframe to the format that user desires: ravenpro .txt or .csv
    """
        
    extension = ".csv"
    sep = ","

    if not cfg["should_csv"]:
        extension = ".txt"
        sep = "\t"
        annotation_df = convert_df_ravenpro(annotation_df)

    filename = f"{cfg['csv_filename']}{extension}"

    csv_path = output_dir / filename
    annotation_df.to_csv(csv_path, sep=sep, index=False)
    print('this is csv path')
    print(csv_path)
    return csv_path

def convert_df_ravenpro(df: pd.DataFrame):
    """
    Converts a dataframe to the format used by RavenPro
    """

    ravenpro_df = df.copy()

    ravenpro_df.rename(columns={
        "start_time": "Begin Time (s)",
        "end_time": "End Time (s)",
        "low_freq": "Low Freq (Hz)",
        "high_freq": "High Freq (Hz)",
        "event": "Annotation",
    }, inplace=True)

    ravenpro_df["Selection"] = np.arange(0, df.shape[0]).astype('int') + 1
    ravenpro_df["View"] = "Waveform 1"
    ravenpro_df["Channel"] = "1"

    return ravenpro_df

def construct_activity_arr(cfg, data_params):
    """
    Constructs DataFrames corresponding to different important ways of storing activity for a deployment session.
    plot_df is an activity grid with date headers and time indices and number of detections as values.
    activity_df is a 2-column dataframe with datetime indices and corresponding number of calls detected for resampling purposes.

    Parameters
    ------------
    csv_name : `str`
        - The detections of bat search-phase calls in each audio file existing in the provided input directory.
        - Stored as "bd2__recover-DATE_UBNA_###.csv"
    ref_audio_files : `List`
        - A list of audio files that should be recorded by the Audiomoth representing the times that were recorded.
    good_audio_files : `List`
        - A list of audio files that are error-free and were fed into the MSDS pipeline.
    output_dir : `str`
        - The path to the output directory where the activity grid and the 2-column activity .csv files will be saved.
    show_PST : `boolean`
        - A flag whether user wants to time in PST instead of UTC.
        - For example, today's 03:00 UTC will become yesterday's 20:00 PST (-7 hrs)

    Returns
    ------------
    plot_df : `pd.DataFrame`
        - Rows corresponding to the time of day ranging, for example, from 03:00 to 13:00 UTC.
        - Columns corresponding to the days of activity ranging, for example, from 2023-06-10 to 2023-06-15
        - Cell value corresponding to the number of detections per 30-min of each day
            - Values are 0 for error-files, 1 for call-absence, number of detections otherwise.
            - Recordings where the Audiomoth experienced errors are colored red.
    """

    csv_tag = cfg["csv_filename"].split('__')[-1]
    ref_datetimes = pd.to_datetime(data_params['ref_audio_files'], format="%Y%m%d_%H%M%S", exact=False)
    activity_datetimes_for_file = ref_datetimes.tz_localize('UTC')
    good_datetimes = pd.to_datetime(data_params['good_audio_files'], format="%Y%m%d_%H%M%S", exact=False)
    if (cfg['cycle_length'] - cfg['duration']) <= 5:
        nodets = 1
    else:
        nodets = (cfg['duration'])/((data_params['resample_in_min']*60))

    dets = pd.read_csv(f'{data_params["output_dir"]}/{cfg["csv_filename"]}.csv')
    dets['ref_time'] = pd.to_datetime(dets['input_file'], format="%Y%m%d_%H%M%S", exact=False)
    activity_dets_arr = pd.DataFrame()
    for group in ['', 'LF', 'HF']:
        if group != '':
            freq_group_df = dets.loc[dets['KMEANS_CLASSES']==group].copy()
        else:
            freq_group_df = dets.copy()
        dets_per_file = freq_group_df.groupby(['ref_time'])['ref_time'].count()
        activity = dets_per_file.reindex(good_datetimes, fill_value=nodets).reindex(ref_datetimes, fill_value=0)

        if (cfg['cycle_length'] - cfg['duration']) > 5:
            activity = activity *(cfg['cycle_length'] / cfg['duration'])
        activity_arr = pd.DataFrame(list(zip(activity_datetimes_for_file, activity)), columns=["date_and_time_UTC", f"{group}num_of_detections"])
        activity_arr = activity_arr.set_index("date_and_time_UTC")
        activity_dets_arr = pd.concat([activity_dets_arr, activity_arr], axis=1)

    activity_dets_arr.to_csv(f"{data_params['output_dir']}/activity__{csv_tag}.csv")

    return activity_dets_arr


def shape_activity_array_into_grid(cfg, data_params, group):

    csv_tag = cfg['csv_filename'].split('__')[-1]

    num_dets = pd.read_csv(f"{data_params['output_dir']}/activity__{csv_tag}.csv", index_col=0)
    num_dets.index = pd.DatetimeIndex(num_dets.index)

    resampled_df = num_dets.resample(data_params["resample_tag"]).sum().between_time(cfg['recording_start'], cfg['recording_end'], inclusive='left')

    activity_datetimes = pd.to_datetime(resampled_df.index.values)
    raw_dates = activity_datetimes.date
    raw_times = activity_datetimes.strftime("%H:%M")

    col_name = f"{group}num_of_detections"
    data = list(zip(raw_dates, raw_times, resampled_df[col_name]))
    activity = pd.DataFrame(data, columns=["Date (UTC)", "Time (UTC)", col_name])
    activity_df = activity.pivot(index="Time (UTC)", columns="Date (UTC)", values=col_name)
    activity_df.columns = pd.to_datetime(activity_df.columns).strftime('%m/%d/%y')
    activity_df.to_csv(f"{data_params['output_dir']}/activity_plot__{group}{csv_tag}.csv")

    return activity_df


def plot_activity_grid(plot_df, data_params, group, show_PST=False, save=True):
    """
    Plots the above-returned plot_df DataFrame that represents activity over a deployment session.

    Parameters
    ------------
    plot_df : `pd.DataFrame`
        - Rows corresponding to the time of day ranging, for example, from 03:00 to 13:00 UTC.
        - Columns corresponding to the days of activity ranging, for example, from 2023-06-10 to 2023-06-15
        - Cell value corresponding to the number of detections per 30-min of each day
    output_dir : `str`
        - The path to the output directory where the activity grid and the 2-column activity .csv files will be saved.
    recover_folder : `str`
        - The name of the recover folder for the input deployment directory: recover-DATE
    audiomoth_folder : `str`
        - The name of the audiomoth SD card # folder for the input deployment directory: UBNA_###
    site_name: `str`
        - The location where the Audiomoth was deployed; Found using the field records.
    show_PST : `boolean`
        - A flag whether user wants to time in PST instead of UTC.
        - For example, today's 03:00 UTC will become yesterday's 20:00 PST (-7 hrs)
    """

    plot_title = group
    if plot_title!='':
        plot_title = group.upper().replace('_', ' ')
    masked_array_for_nodets = np.ma.masked_where(plot_df.values==0, plot_df.values)
    cmap = plt.get_cmap('viridis')
    cmap.set_bad(color='red', alpha=1.0)
    plot_dates = [''] * len(plot_df.columns)
    plot_dates[::3] = plot_df.columns[::3]
    plot_times = [''] * len(plot_df.index)
    plot_times[::3] = plot_df.index[::3]

    plt.rcParams.update({'font.size': 16})
    plt.figure(figsize=(12, 8))
    plt.title(f"{plot_title}Activity from {data_params['site']}", loc='left', y=1.05)
    plt.imshow(masked_array_for_nodets, cmap=cmap, norm=colors.LogNorm(vmin=1, vmax=10e3))
    plt.yticks(np.arange(0, len(plot_df.index))-0.5, plot_times, rotation=45)
    plt.xticks(np.arange(0, len(plot_df.columns))-0.5, plot_dates, rotation=45)
    plt.grid(which='both')
    plt.ylabel('UTC Time (HH:MM)')
    if show_PST:
        plt.ylabel('PST Time (HH:MM)')
    plt.xlabel('Date (MM/DD/YY)')
    plt.colorbar()
    if save:
        plt.savefig(f"{data_params['output_dir']}/activity_plot__{group}{data_params['recover_folder']}_{data_params['audiomoth_folder']}.png", bbox_inches='tight', pad_inches=0.5)
    plt.tight_layout()
    plt.show()

def construct_cumulative_activity(data_params, cfg, group, save=True):
    """
    Constructs a cumulative appended DataFrame grid using dask.dataframe.
    This DataFrame gathers all detected activity contained in output_dir for a given site.

    Parameters
    ------------
    output_dir : `str`
        - The output directory that will save the cumulative dataframes.
    site : `str`
        - The site we wish to assemble all activity from.
    resample_tag : `str`
        - The resample_tag associated with resampling: choose above 30T like 1H, 2H or D.

    Returns
    ------------
    activity_df : `pd.DataFrame`
        - Rows corresponding to the time of day ranging, for example, from 03:00 to 13:00 UTC.
        - Columns corresponding to the days of activity ranging, for example, from 2023-06-10 to 2023-06-15
        - Cell value corresponding to the number of detections per 30-min of each day
            - Values are 0 for error-files, 1 for call-absence, number of detections otherwise.
            - Recordings where the Audiomoth experienced errors are colored red.
    """

    new_df = dd.read_csv(f"{Path(__file__).parent}/../output_dir/{data_params['selection_of_dates']}/{data_params['site']}/activity__*.csv", assume_missing=True).compute()
    new_df["date_and_time_UTC"] = pd.to_datetime(new_df["date_and_time_UTC"], format="%Y-%m-%d %H:%M:%S%z")

    resampled_df = new_df.resample(data_params["resample_tag"], on="date_and_time_UTC").sum().between_time(cfg['recording_start'], cfg['recording_end'], inclusive='left')

    activity_datetimes = pd.to_datetime(resampled_df.index.values)
    raw_dates = activity_datetimes.date
    raw_times = activity_datetimes.strftime("%H:%M")
    mask = resampled_df.columns.str.contains(f'{group}.*')
    if group!='':
        mask = resampled_df.columns.str.contains(f'{group}.*')
        selected_group = resampled_df.loc[:,mask]
        if selected_group.shape[1]>2:
            middle_col = selected_group.iloc[:,1]
            middle_col.loc[middle_col<=1.0] = 0
        data = list(zip(raw_dates, raw_times, selected_group.sum(axis=1)))
    else:
        data = list(zip(raw_dates, raw_times, resampled_df[f'{group}num_of_detections']))
    activity = pd.DataFrame(data, columns=["Date (UTC)", "Time (UTC)", f'{group}num_of_detections'])
    activity_df = activity.pivot(index="Time (UTC)", columns="Date (UTC)", values=f'{group}num_of_detections')
    activity_df.columns = pd.to_datetime(activity_df.columns).strftime('%m/%d/%y')
    cum_plots_dir = f'{Path(__file__).parent}/../output_dir/cumulative_plots/'
    if save:
        activity_df.to_csv(f'{cum_plots_dir}/cumulative_activity__{group}{data_params["site"].split()[0]}_{data_params["resample_tag"]}.csv')

    return activity_df

def plot_cumulative_activity(activity_df, data_params, group, save=True):
    """
    Plots the cumulative appended DataFrame grid of all detected activity a given site.

    Parameters
    ------------
    activity_df : `pd.DataFrame`
        - Rows corresponding to the time of day ranging, for example, from 03:00 to 13:00 UTC.
        - Columns corresponding to the days of activity ranging, for example, from 2023-06-10 to 2023-06-15
        - Cell value corresponding to the number of detections per 30-min of each day
    output_dir : `str`
        - The output directory that will save the cumulative dataframes.
    site : `str`
        - The site we wish to assemble all activity from.
    resample_tag : `str`
        - The resample_tag associated with resampling: choose above 30T like 1H, 2H or D.
    """

    plot_title = group
    if plot_title!='':
        if len(plot_title)==2:
            plot_title = group + ' '
        else:
            plot_title = group.upper().replace('_', ' ')
    masked_array_for_nodets = np.ma.masked_where(activity_df.values==0, activity_df.values)

    activity_times = pd.DatetimeIndex(activity_df.index).tz_localize('UTC')
    ylabel = 'UTC'
    if data_params["show_PST"]:
        activity_times = activity_times.tz_convert(tz='US/Pacific')
        ylabel = 'PST'
    activity_times = activity_times.strftime("%H:%M")

    cmap = plt.get_cmap('viridis')
    cmap.set_bad(color='red')
    plot_dates = [''] * len(activity_df.columns)
    plot_dates[::7] = activity_df.columns[::7]
    plot_times = [''] * len(activity_times)
    plot_times[::3] = activity_times[::3]

    activity_dates = pd.to_datetime(activity_df.columns.values, format='%m/%d/%y')
    activity_lat = [SEATTLE_LATITUDE]*len(activity_dates)
    activity_lon = [SEATTLE_LONGITUDE]*len(activity_dates)
    sunrise_time = pd.DatetimeIndex(suncalc.get_times(activity_dates, activity_lon, activity_lat)['sunrise_end'])
    sunset_time = pd.DatetimeIndex(suncalc.get_times(activity_dates, activity_lon, activity_lat)['sunset_start'])
    sunrise_seconds_from_midnight = sunrise_time.hour * 3600 + sunrise_time.minute*60 + sunrise_time.second
    sunset_seconds_from_midnight = sunset_time.hour * 3600 + sunset_time.minute*60 + sunset_time.second

    recent_sunrise = sunrise_time.tz_convert(tz="US/Pacific").strftime("%H:%M")[-1]
    recent_sunset = sunset_time.tz_convert(tz="US/Pacific").strftime("%H:%M")[-1]

    plt.rcParams.update({'font.size': 2*len(plot_dates)**0.5})
    plt.figure(figsize=(len(plot_dates)/4, len(plot_times)/4))
    plt.title(f"{plot_title}Activity (# of calls) from {data_params['site']}", loc='center', y=1.05, fontsize=(3)*len(plot_dates)**0.5)
    plt.plot(np.arange(0, len(plot_dates)), ((sunset_seconds_from_midnight / (30*60)) % len(plot_times)) - 0.5, 
            color='white', linewidth=5, linestyle='dashed', label=f'Time of Sunset (Recent: {recent_sunset} PST)')
    plt.axhline(y=14-0.5, linewidth=5, linestyle='dashed', color='white', label='Midnight 0:00 PST')
    plt.plot(np.arange(0, len(plot_dates)), ((sunrise_seconds_from_midnight / (30*60)) % len(plot_times)) - 0.5, 
            color='white', linewidth=5, linestyle='dashed', label=f'Time of Sunrise (Recent: {recent_sunrise} PST)')
    plt.imshow(masked_array_for_nodets, cmap=cmap, norm=colors.LogNorm(vmin=1, vmax=10e3))
    plt.yticks(np.arange(0, len(plot_times))-0.5, plot_times, rotation=30)
    plt.xticks(np.arange(0, len(plot_dates))-0.5, plot_dates, rotation=30)
    plt.ylabel(f'{ylabel} Time (HH:MM)')
    plt.xlabel('Date (MM/DD/YY)')
    plt.colorbar()
    plt.legend(loc=3, fontsize=(2*len(plot_dates)**0.5))
    plt.grid(which='both')
    plt.tight_layout()
    cum_plots_dir = f'{Path(__file__).parent}/../output_dir/cumulative_plots/2023'
    if save:
        plt.savefig(f'{cum_plots_dir}/cumulative_activity__2023_{group}{data_params["site"].split()[0]}_{data_params["resample_tag"]}.png', 
                    bbox_inches='tight')
        file = f'{cum_plots_dir}/cumulative_activity__{group}{data_params["site"].split()[0]}_{data_params["resample_tag"]}.png'
        print(file)
    #plt.show()

def delete_segments(necessary_paths):
    """
    Deletes the segments whose paths are stored in necessary_paths

    Parameters
    ------------
    necessary_paths : `List`
        - A list of dictionaries generated from generate_segmented_paths()
    """

    for path in necessary_paths:
        path['audio_file'].unlink(missing_ok=False)


def run_pipeline_on_file(file, cfg):
    bd_preds = pd.DataFrame()

    if not cfg['output_dir'].is_dir():
        cfg['output_dir'].mkdir(parents=True, exist_ok=True)
    if not cfg['tmp_dir'].is_dir():
        cfg['tmp_dir'].mkdir(parents=True, exist_ok=True)

    if (cfg['run_model']):
        cfg["csv_filename"] = f"batdetect2_pipeline_{file.name.split('.')[0]}"
        print(f"Generating detections for {file.name}")
        segmented_file_paths = generate_segmented_paths([file], cfg)
        file_path_mappings = initialize_mappings(segmented_file_paths, cfg)
        bd_preds = run_models(file_path_mappings)
        save = True
        if save:
            _save_predictions(bd_preds, cfg['output_dir'], cfg)
            print('cfg[out_file]')
            print(cfg['output_dir'])
        delete_segments(segmented_file_paths)

    return bd_preds


def run_pipeline_for_individual_files_with_df(cfg):

    good_location_df, data_params = get_params_relevant_to_data_at_location(cfg)

    bd_preds = pd.DataFrame()

    if not data_params['output_dir'].is_dir():
        data_params['output_dir'].mkdir(parents=True, exist_ok=True)
    if not cfg['tmp_dir'].is_dir():
        cfg['tmp_dir'].mkdir(parents=True, exist_ok=True)

    if (cfg['run_model']):
        for file in data_params['good_audio_files']:
            cfg["csv_filename"] = f"bd2__{data_params['site'].split()[0]}_{file.name.split('.')[0]}"
            if cfg['skip_existing'] & (data_params['output_dir'] / f"{cfg['csv_filename']}.csv").is_file():
                print(f'Detections for this {file.name} have already been generated!')
            else:
                print(f"Generating detections for {file.name}")
                recover_folder = good_location_df.loc[good_location_df['file_path'] == str(file), 'recover_folder'].values[0]
                audiomoth_folder = good_location_df.loc[good_location_df['file_path'] == str(file), "sd_card_num"].values[0]
                print(f"This file exists under {recover_folder}/UBNA_{audiomoth_folder}")
                segmented_file_paths = generate_segmented_paths([file], cfg)
                file_path_mappings = initialize_mappings(segmented_file_paths, cfg)
                if (cfg["num_processes"] <= 6):
                    bd_preds = run_models(file_path_mappings)
                else:
                    bd_preds = apply_models(file_path_mappings, cfg)
                bd_preds["Site name"] = data_params['site']
                bd_preds["Recover Folder"] = recover_folder
                bd_preds["SD Card"] = audiomoth_folder
                bd_preds["File Duration"] = f'{cfg["duration"]}'
                _save_predictions(bd_preds, data_params['output_dir'], cfg)
                delete_segments(segmented_file_paths)

    return bd_preds


def get_params_relevant_to_data_at_location(cfg):
    data_params = dict()
    data_params['site'] = cfg['site']
    print(f"Searching for files from {cfg['site']} in {cfg['month']} {cfg['year']}")

    hard_drive_df = dd.read_csv(f'{Path(__file__).parent}/../output_dir/ubna_data_*_collected_audio_records.csv', dtype=str).compute()
    if 'Unnamed: 0' in hard_drive_df.columns:
        hard_drive_df.drop(columns='Unnamed: 0', inplace=True)
    hard_drive_df["datetime_UTC"] = pd.DatetimeIndex(hard_drive_df["datetime_UTC"])
    hard_drive_df.set_index("datetime_UTC", inplace=True)
    
    files_from_location = filter_df_with_location(hard_drive_df, cfg)
    data_params['output_dir'] = cfg["output_dir"] / data_params["site"]
    print(f"Will save csv file to {data_params['output_dir']}")

    data_params['ref_audio_files'] = sorted(list(files_from_location["file_path"].apply(lambda x : Path(x)).values))
    file_status_cond = files_from_location["file_status"] == "Usable for detection"
    file_duration_cond = np.isclose(files_from_location["file_duration"].astype('float'), cfg['duration'])
    good_location_df = files_from_location.loc[file_status_cond&file_duration_cond]
    data_params['good_audio_files'] = sorted(list(good_location_df["file_path"].apply(lambda x : Path(x)).values))

    if data_params['good_audio_files'] == data_params['ref_audio_files']:
        print("All files from deployment session good!")
    else:
        print("Error files exist!")

    print(f"Will be looking at {len(data_params['good_audio_files'])} files from {data_params['site']}")

    return good_location_df, data_params


def filter_df_with_location(ubna_data_df, cfg):
    site_name_cond = ubna_data_df["site_name"] == cfg['site']
    file_year_cond = ubna_data_df.index.year == (dt.datetime.strptime(cfg['year'], '%Y')).year
    file_month_cond = ubna_data_df.index.month == (dt.datetime.strptime(cfg['month'], '%B')).month
    minute_cond = np.logical_or((ubna_data_df.index).minute == 30, (ubna_data_df.index).minute == 0)
    datetime_cond = np.logical_and((ubna_data_df.index).second == 0, minute_cond)
    file_error_cond = np.logical_and((ubna_data_df["file_duration"]!='File has no comment due to error!'), (ubna_data_df["file_duration"]!='File has no Audiomoth-related comment'))
    all_errors_cond = np.logical_and((ubna_data_df["file_duration"]!='Is empty!'), file_error_cond)
    file_date_cond = np.logical_and(file_year_cond, file_month_cond)

    filtered_location_df = ubna_data_df.loc[site_name_cond&datetime_cond&file_date_cond&all_errors_cond].sort_index()
    filtered_location_nightly_df = filtered_location_df.between_time(cfg['recording_start'], cfg['recording_end'], inclusive="left")

    return filtered_location_nightly_df


def run_pipeline_for_session_with_df(cfg):

    data_params = get_params_relevant_to_data(cfg)
    cfg["csv_filename"] = f"bd2__{data_params['recover_folder']}_{data_params['audiomoth_folder']}"

    bd_preds = pd.DataFrame()

    if not data_params['output_dir'].is_dir():
        data_params['output_dir'].mkdir(parents=True, exist_ok=True)
    if not cfg['tmp_dir'].is_dir():
        cfg['tmp_dir'].mkdir(parents=True, exist_ok=True)

    if (cfg['run_model']):
        segmented_file_paths = generate_segmented_paths(data_params['good_audio_files'], cfg)
        file_path_mappings = initialize_mappings(segmented_file_paths, cfg)
        if (cfg["num_processes"] <= 6):
            bd_preds = run_models(file_path_mappings)
        else:
            bd_preds = apply_models(file_path_mappings, cfg)
        bd_preds["Recover Folder"] = data_params['recover_folder']
        bd_preds["SD Card"] = data_params["audiomoth_folder"]
        bd_preds["Site name"] = data_params['site']
        _save_predictions(bd_preds, data_params['output_dir'], cfg)
        delete_segments(segmented_file_paths)

    if (cfg['generate_fig']):
        data_params['resample_in_min'] = 30
        data_params['resample_tag'] = f"{data_params['resample_in_min']}T"
        construct_activity_arr(cfg, data_params)
        for group in ['', 'LF', 'HF']:
            activity_df = shape_activity_array_into_grid(cfg, data_params, group)
            plot_activity_grid(activity_df, data_params, group, save=True)
            if data_params["site"] != "(Site not found in Field Records)":
                data_params['selection_of_dates'] = 'recover-2024*'
                cumulative_activity_df = construct_cumulative_activity(data_params, cfg, group)
                data_params['show_PST'] = False
                plot_cumulative_activity(cumulative_activity_df, data_params, group)

    return bd_preds

def get_params_relevant_to_data(cfg):
    data_params = dict()
    data_params['recover_folder'] = cfg['recover_folder']
    data_params["audiomoth_folder"] = f"UBNA_{cfg['sd_unit']}"
    print(f"Searching for files from {cfg['recover_folder']} and {data_params['audiomoth_folder']}")

    cur_data_records = dd.read_csv(f'{Path(__file__).parent}/../output_dir/ubna_data_04_collected_audio_records.csv', dtype=str).compute()
    if 'Unnamed: 0' in cur_data_records.columns:
        cur_data_records.drop(columns='Unnamed: 0', inplace=True)
    cur_data_records["datetime_UTC"] = pd.DatetimeIndex(cur_data_records["datetime_UTC"])
    cur_data_records.set_index("datetime_UTC", inplace=True) 
    
    files_from_deployment_session = filter_df_with_deployment_session(cur_data_records, data_params['recover_folder'], cfg)
    site_name = files_from_deployment_session["site_name"].values[0]
    data_params["site"] = site_name
    if data_params["site"] != "(Site not found in Field Records)":
        data_params['output_dir'] = cfg["output_dir"] / data_params["site"]
    elif cfg['site']!='none':
        data_params['output_dir'] = cfg["output_dir"] / cfg['site']
        data_params['site'] = cfg['site']
    else:
        data_params['output_dir'] = cfg["output_dir"] / f"UBNA_{cfg['sd_unit']}"
    print(f"Will save csv file to {data_params['output_dir']}")

    data_params['ref_audio_files'] = sorted(list(files_from_deployment_session["file_path"].apply(lambda x : Path(x)).values))
    file_status_cond = files_from_deployment_session["file_status"] == "Usable for detection"
    file_duration_cond = files_from_deployment_session["file_duration"].astype('float') >= (cfg['duration'])
    good_deploy_session_df = files_from_deployment_session.loc[file_status_cond & file_duration_cond]
    data_params['good_audio_files'] = sorted(list(good_deploy_session_df["file_path"].apply(lambda x : Path(x)).values))

    if data_params['good_audio_files'] == data_params['ref_audio_files']:
        print("All files from deployment session good!")
    else:
        print("Error files exist!")

    return data_params

def filter_df_with_deployment_session(ubna_data_df, recover_folder, cfg):
    recover_folder_cond = ubna_data_df["recover_folder"] == recover_folder
    sd_unit_cond = ubna_data_df["sd_card_num"] == cfg["sd_unit"]
    filtered_location_df = ubna_data_df.loc[recover_folder_cond&sd_unit_cond].sort_index()

    start_time, end_time = get_recording_period(Path(filtered_location_df['file_path'].values[0]).parent)
    file_minutes = pd.to_datetime(filtered_location_df.index.minute, format="%M")
    offset_from_config = dt.timedelta(minutes=dt.datetime.strptime(start_time, "%H:%M").minute)
    corrected_minutes = (file_minutes - offset_from_config).minute
    datetime_cond = np.logical_and(np.mod(corrected_minutes, (cfg['cycle_length']/60)) == 0, filtered_location_df.index.second == 0)
    file_error_cond = np.logical_and((filtered_location_df["file_duration"]!='File has no comment due to error!'), (filtered_location_df["file_duration"]!='File has no Audiomoth-related comment'))
    all_errors_cond = np.logical_and((filtered_location_df["file_duration"]!='Is empty!'), file_error_cond)
    filtered_location_df = filtered_location_df.loc[datetime_cond&all_errors_cond].sort_index()
    filtered_location_nightly_df = filtered_location_df.between_time(cfg['recording_start'], cfg['recording_end'], inclusive="left")

    return filtered_location_nightly_df


def get_recording_period(audio_dir):
    """
    Gets configured recording period of Audiomoth over a deployment session using CONFIG.TXT.

    Parameters
    ------------
    audio_dir : `str`
        - The directory of Audiomoth recordings + CONFIG.TXT corresponding to a deployment session.

    Returns
    ------------
    start_time : `str`
        - The start time of the configured recording period.
    end_time : `str`
        - The end time of the configured recording period.
    """
    
    config_path = audio_dir / 'CONFIG.TXT'
    if (config_path.is_file()):
        config_details = pd.read_csv(config_path, header=0, index_col=0, sep=" : ", engine='python').transpose()
        config_details.columns = config_details.columns.str.strip()
        recording_period = config_details['Recording period 1'].values[0]
        period_tokens = recording_period.split(' ')
    else:
        period_tokens = ["00:00", "-", "23:59"]
    start_time = period_tokens[0]
    end_time = period_tokens[2]
    if end_time == "24:00":
        end_time = "23:59"

    return start_time, end_time

def parse_args():
    """
    Defines the command line interface for the pipeline.
    """

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input_audio",
        type=str,
        help="the directory of WAV files to process",
        default="none"
    )
    parser.add_argument(
        "--recover_folder",
        type=str,
        help="The recover-DATE folder we have saved files into",
        default="none"
    )
    parser.add_argument(
        "--sd_unit",
        type=str,
        help="The SD card # we have saved files into",
        default="none"
    )
    parser.add_argument(
        "--site",
        type=str,
        help="The site we have collected files from",
        default="none"
    )
    parser.add_argument(
        "--year",
        type=str,
        help="The full year from which we want files",
        default="none"
    )
    parser.add_argument(
        "--month",
        type=str,
        help="The month's full name from which we want files",
        default="none"
    )
    parser.add_argument(
        "--recording_start",
        type=str,
        help="The start time of files to look at (inclusive)"
    )
    parser.add_argument(
        "--recording_end",
        type=str,
        help="The end time of files to look at (non-inclusive)"
    )
    parser.add_argument(
        "--duration",
        type=int,
        help="The length of audio files we want to select",
        default=1795
    )
    parser.add_argument(
        "--cycle_length",
        type=int,
        help="The time between each file",
        default=1800
    )
    parser.add_argument(
        "--output_directory",
        type=str,
        help="the directory where the .csv file goes",
        default="output_dir",
    )
    parser.add_argument(
        "--tmp_directory",
        type=str,
        help="the temp directory where the audio segments go",
        default="output/tmp",
    )
    parser.add_argument(
        "--run_model",
        action="store_true",
        help="Do you want to run the model? As opposed to just generating the figure",
    )
    parser.add_argument(
        "--generate_fig",
        action="store_true",
        help="Do you want to generate and save a corresponding summary figure?",
    )
    parser.add_argument(
        "--csv",
        action="store_true",
        help="Generate CSV instead of TSV",
    )
    parser.add_argument(
        "--skip_existing",
        action="store_true",
        help="skip generating detections for files if .csv already exist",
    )
    parser.add_argument(
        "--num_processes",
        type=int,
        default=4,
    )
    return vars(parser.parse_args())


if __name__ == "__main__":
    print('in main')
    args = parse_args()
    print(args['input_audio'])
    cfg = get_config()
    cfg["input_audio"] = args['input_audio']
    cfg["recover_folder"] = args["recover_folder"]
    cfg["sd_unit"] = args["sd_unit"]
    cfg["site"] = args["site"]
    cfg["year"] = args["year"]
    cfg["month"] = args["month"]
    cfg['recording_start'] = args['recording_start']
    cfg['recording_end'] = args['recording_end']
    cfg['duration'] = args['duration']
    cfg['cycle_length'] = args['cycle_length']
    cfg["output_dir"] = Path(args["output_directory"])
    cfg["tmp_dir"] = Path(args["tmp_directory"])
    cfg["run_model"] = args["run_model"]
    cfg["generate_fig"] = args["generate_fig"]
    cfg["should_csv"] = args["csv"]
    cfg["skip_existing"] = args['skip_existing']
    cfg["num_processes"] = args["num_processes"]

    if cfg['input_audio']!='none':
        if Path(cfg['input_audio']).is_file():
            print('detected input audio file')
            run_pipeline_on_file(Path(cfg['input_audio']), cfg)
        elif Path(cfg['input_audio']).is_dir():
            input_dir = Path(cfg['input_audio'])
            for file in input_dir.iterdir():
                cfg['input_audio'] = file
                run_pipeline_on_file(file, cfg)

    if cfg["recover_folder"]!="none" and cfg["sd_unit"]!="none":
        run_pipeline_for_session_with_df(cfg)

    if cfg['site']!="none" and cfg["year"]!="none" and cfg["month"]!="none":
        run_pipeline_for_individual_files_with_df(cfg)