# BattyBirdNET - Bat Sound Analyzer 

**Note: The system is under heavy development and not (as yet) fit for production use. You are welcome to try it and send feedback.**
## Purpose

The purpose is to assist in the automated classification of bat calls. There are some excellent classifiers out there. However, most are for other animal groups, notably birds, or are limited in their use to researchers. The aim here is to provide a solid classifier for as many regions of the planet as possible that can be built into inexpensive systems for citizen scientists. It builds upon the work of the BirdNET open source product family that has a similar aim for birds. The BirdNET systems are using a sampling frequency that is too low to capture bat echo location calls. So here I use the system at significantly higher sampling rates of 256kHz (default) and cross train a classifier on the BirdNET artificial neural networks to identify bats. Think of a bat as a bird singing three times as fast. Once such a cross trained bat network has the necessary performance, I intend to integrate it into the BirdNET-Pi framework in order to run them 24/7 in self-assembled recoding stations.
You can most definitely already use the bat trained classifier with the analyzer scripts to assist (do not just rely on it for e.g. biodiversity assessments) in identifying bat calls.

Used by the automated, real-time bat detector BattyBirdNET-Pi (https://github.com/rdz-oss/BattyBirdNET-Pi)

Key words: bat identification, bat detector, BirdNET-Analyzer, DNN, machine learning, transfer learning, biodiverity , monitoring

### License

Enjoy! Feel free to use BattyBirdNET for your acoustic analyses and research. If you do, please cite as:
``` bibtex
@misc{Zinck2023,
  author = {Zinck, R.D.},
  title = {BattyBirdNET - Bat Sound Analyzer},
  year = {2023},
  publisher = {GitHub},
  journal = {GitHub repository},
  howpublished = {\url{https://github.com/rdz-oss/BattyBirdNET-Analyzer }}
}
```
LICENSE: http://creativecommons.org/licenses/by-nc-sa/4.0/  
Also consider the references at the end of the page.

## Which species are covered ?
| North America                                         | Europe & UK  (collecting data)                    |
|:------------------------------------------------------|:--------------------------------------------------|
| Antrozous pallidus - Pallid bat                       | Barbastella barbastellus - Western barbastelle    
| Corynorhinus rafinesquii - Rafinesque's big-eared bat | Eptesicus nilssonii - Northern bat                
| Corynorhinus townsendii - Townsend's big-eared bat    | Eptesicus serotinus - Serotine bat                
| Eptesicus fuscus - Big brown bat                      | Hypsugo savii - Savis pipistrelle                 
| Euderma maculatum - Spotted bat                       | Miniopterus schreibersii - Common bent-wing bat   
| Eumops floridanus - Florida bonneted                  | Myotis alcathoe - Alcathoe bat                    
| Eumops perotis - Greater mastiff bat                  | Myotis bechsteinii - Bechsteins bat               
| Idionycteris phyllotis - Allen's big-eared bat        | Myotis brandtii - Brandt bat                      
| Lasionycteris noctivagans - Silver-haired bat         | ( Myotis capaccinii - Long-fingered bat )         
| Lasiurus blossevillii - Western red bat               | Myotis dasycneme - Pond bat                       
| Lasiurus borealis - Eastern red bat                   | Myotis daubentonii - Daubentons bat               
| Lasiurus cinereus - Hoary bat                         | Myotis emarginatus - Geoffroys bat                
| Lasiurus intermedius - Northern yellow bat            | Myotis myotis - Greater mouse-eared bat           
| Lasiurus seminolus - Seminole bat                     | Myotis mystacinus - Whiskered bat                 
| Lasiurus xanthinus - Western yellow bat               | Myotis nattereri - Natterers bat                  
| Myotis austroriparius - Southeastern myotis           | ( Nyctalus lasiopterus - Greater noctule bat )    
| Myotis californicus - California bat                  | Nyctalus leisleri - Lesser noctule                
| Myotis ciliolabrum - Western small-footed myotis      | Nyctalus noctula - Common noctule                 
| Myotis evotis - Western long-eared bat                | Pipistrellus kuhlii - Kuhls pipistrelle           
| Myotis grisescens - Gray bat                          | ( Pipistrellus maderensis - Madeira pipistrelle ) 
| Myotis leibii - Eastern small-footed bat              | Pipistrellus nathusii - Nathusius pipistrelle     
| Myotis lucifugus - Little brown bat                   | Pipistrellus pipistrellus - Common pipistrelle    
| Myotis septentrionalis - Northern long-eared bat      | Pipistrellus pygmaeus - Soprano pipistrelle       
| Myotis sodalis - Indiana bat                          | Plecotus spec. - Long eared bat                   
| Myotis thysanodes - Fringed bat                       | ( Rhinolophus blasii - Blasius horseshoe bat  )   
| Myotis velifer - Cave bat                             | Rhinolophus ferrumequinum - Greater horseshoe bat 
| Myotis volans - Long-legged bat                       | Rhinolophus hipposideros - Lesser horseshoe bat   
| Myotis yumanensis - Yuma bat                          | ( Tadarida teniotis - European free-tailed bat )  
| Nycticeius humeralis - Evening bat                    | Vespertilio murinus - Parti-coloured bat          
| Nyctinomops femorosaccus - Pocketed free-tailed bat   |
| Nyctinomops macrotis - Big free-tailed bat            |
| Parastrellus hesperus - Canyon bat                    |
| Perimyotis subflavus - Tricolored bat                 |
| Tadarida brasiliensis - Brazilian free-tailed bat     |                                           

[//]: # (## Try the demo at huggingface.co !)

[//]: # (If you have small &#40;a few seconds&#41; .wav or .flac recordings of bats you can try the online demo. It is hosted on a small)

[//]: # (container &#40;2 vcpu&#41; so you need to install your own system &#40;see below&#41; if you want to analyze larger data sets. )

[//]: # (There are 144kHz and 256kHz classifiers. The basic demo runs on 144kHz. When testing a new version, I will)

[//]: # (however enable a 256kHz version &#40;for Bavaria&#41;.)

[//]: # ()
[//]: # (https://huggingface.co/spaces/Amazetl/BattyBirdNET-Analyze-Demo)

[//]: # ()
[//]: # (If you are from the UK, you can crosscheck e.g. with batdetect2)

[//]: # ()
[//]: # (https://huggingface.co/spaces/macaodha/batdetect2)

## Methods and data
The detection works by transfer learning from the bird detection network BirdNET v2.4. This network operates on 48000Hz and 3 second sampling intervals. This will not work for bats as their calls go much higher in frequency rates. Since the network is designed to identify bird calls it is still usefull for cross training for bat calls once the frequency range is adjusted. There are several realistic candidates for such frequency rates, including

* 144000 Hz at 1 second intervalls - bat sound up to 72kHz considered
* 288000 Hz at 0.5 second intervalls - bat sounds uo to 144kHz considered
* 360000 Hz at 0.4 second intervals - bat sounds up to 180kHz considered

All of which seem plausible enough for detecting most European and North American bat species. It depends on the hardware (microphones) available to you and the calls of the bat species in your area. The above combinations arise form the expected input to the BirdNET artificial neural network ( 144000 = 48000 * 3). An advantage that comes with this is that not single calls, but all calls  that occur within a second are used to identify the bat allowing for more context/correlation than many traditional bat classifiers consider. In general there is a trade-off between this context and the frequency range you allow for. The value fo BattyBirdNET at 256kHz is set to a compromise for cost and range of many bat species and available microphones.

The data for North American bats comes from the NABAT machine learning data set. The data for Europe was assembled from the Animal Sound Archive Berlin, the ChiroVox database and the xeno-canto database. It contains echolocation as well as social and distress calls in different quantities for each species.

The cross training / transfer learning itself uses the framework provided by BirdNET-Analyzer originally intended for fine tuneing the model to local bird calls or other wildlife in the human audible range. Essentially, it puts a thin layer of a linear classifier on the output of the BirdNET artificial neural network. Appears to also work for bats if sampling frequencies are adjusted. To cross train your own classifier on top of BirdNET set the config parameters in config.py and run e.g.
```  sh
 python3 train.py --i ../path/to/data --o ./path/to/file-name-you-want.tflite
```
This expects that your training data is contained in subfolders that have the following name structure 'Lantin name_Common name' such as e.g. 'Antrozous pallidus_Pallid bat'. The labels are parsed from the folder names. You can also have folders for 'noise' or 'background'.

### Data sets
The Bavaria data is under the http://creativecommons.org/licenses/by-nc-sa/4.0/  license. You are welcome to use it accordingly, e.g.
for teaching and research,OSS software and systems as well as for other non-commercial purposes. 
The Bavaria data set also encompasses UK and nordic species. The data is a random selection of up to 100 samples per species
from data from xeno-canto, chirovox, animal sound library berlin, as well as individuals (R. Zinck (GER), K. Richards (UK)).

If you have data, consider contacting me as the classifiers can only be as good as the data sets they are trained with.
Help us reach the goal of at least 100  samples (3 second recordings) per species!
 
![Samples per species ](./assets/Bavaria-256kHz-100.png?raw=true "Samples per species in Bavaria-256kHz-100 data set.")

Currently, you can download the data [ here ](https://cloud.h2887844.stratoserver.net/s/Txpq4GyembeWDa3) (subject to change) using the password "BattyBirdNET-data".
There are 1700 samples at 256kHz summing up to (compressed) 5.5 GB, uncompressed about 8.6 GB.

## Classifiers
The classifiers are used together with BirdNET to identify the bats. The audio file you provide is resampled to 256 kHz 
and presented to BirdNET in a sequences of 0.5625 seconds. 
It can hence pick up frequencies of up to 256kHz/2  = 128kHz. 
The system can also be run at higher frequencies (see methods). 
Essentially, BirdNET believes that a bird made these half second bat sounds in three seconds. 
It generates a representation of the audio signal (embedding) which is then taken by the classifiers 
listed below to identify the bat. The classifier 'knows' that this is a bat and not a bird as 
BirdNET would believe. The classifiers are trained with cricket and environmental noise. 
This reduces their precision, but makes them more robust against environmental noises.

As they are in development, not all regions will be available at all times. The 144kHz classifiers can be activated
in bat_ident.py using the argument --kHz 144 .

| Classifier       |  Range      |     Training set size    | Validation loss and precision |
|:-------|:------|:------| :------|
|**EU** | Covers 29 species. |  2200+ calls. | 
|**Bavaria** | Covers 24 species. |  2000+ calls  |  
|**USA** | Covers 34 species. | max. 200 calls/species.  |  
|**Scotland** | Covers 10 species. |  1200+ calls. | 
| **UK** | Covers 16 species. | 1500+ calls. | 

Some occasional 'guests' are considered but definitely not all possible ones. The performance of the classifiers depends mostly on the quality and size of the data set used in training. The amount of samples for each species vary. So does the context of the calls. The BattyBirdNETs training data set contains free fly, hunting, social calls, calls during release and in enclosures. The amount of these vary for each species. To avoid overfitting, the classifiers were trained with noise.
The UK, Sweden, Scotland, Bavaria classifiers are trained on subsets of this data set. For the US data, see the lik to the NABAT data site below.

## Install
You can follow the same procedure as for the BirdNET-Analyzer [see here](./README_BIRDNET_ANALYZER.adoc). Just remember to use this repository.

If you want to generate spectrograms, you need to install 'sox' for your platform and make sure it is in your systems PATH variable.

To use the graphical UI, you will need to upse pip3 to install pywebview and gradio.

## Usage
### Clients analyze.py and bat_ident.py
To identify bats, load your audio data into the folder named 'put-your-files-here'. The files can be in .wav (recommended), .flac, .mp3, .ogg or .m4a format.  The analysis is set to standard settings that should work for most by default. If you are fine with the EU classfier and hava python 3.10 version installed (check with python3 --version), then
``` sh
python3 bat_ident.py
```
is all you need to do to run an analysis on all autio files in that directory. Results will appear in a 'put-your-files-here/results' folder in .csv format. The audio files are analyzed and for each second one or two potential species are listed. These are the most likely bat species to made made the calls in that second.
You can also use the more verbose analyze.py
``` sh
python3 analyze.py --i put-your-files-here/ --o put-your-files-here/results --classifier checkpoints/bats/v1.0/BattyBirdNET-Bavaria-144kHz.tflite
```
There are several options available, most natably the area setting, e.g.
``` sh
python3 bat_ident.py --area Scotland
```
that uses a more area specific subset of bats and hence can reduce some classification erros. You can set the above classifiers via the '--area' flag. Further, you can also set analysis related parameters such as 

``` sh
--min_conf  Minimum confidence threshold. Values in [0.01, 0.99]. Defaults to 0.1. 
--overlap   Overlap of prediction segments. Values in [0.0, 2.9]. Defaults to 0.0. 
--rtype     Specifies output format. Values in ['table', 'audacity', 'r',  'kaleidoscope', 'csv']. 
```
and hardware related parameters
``` sh
--threads    Number of CPU threads.
--batchsize  Number of samples to process at the same time.
```
you can also provide custom input and output dirctories
``` sh
--i  Path to input file or folder.
--o  Path to output file or folder.
```
A more complex example might look like this
``` sh
python3 bat_ident.py --location Bavaria --i test_data/Bavaria --o test_data/Bavaria/results --min_conf 0.4 --overlap 0.3
```

### Graphical user interface
Currently single file and batch file analysis are supported with English labels. You need to have pywebview and gradio installed, e.g. by
``` sh
pip3 install pywebview gradio
```
To start the GUI, use
``` sh
python3 bat_gui.py
```
it opens up a window and alternatively, you can use it from your browser on http://127.0.0.1:7860 .
Once you have analysis files, you can use the segmentats tab to extract segments. 

### Extracting identified segments and plotting spectrograms
Once you ran bat_ident.py and have a result file, you can obtain the segmented audio files sorted by detected species using 
``` sh
python3 segments.py --audio path/to/input/audio --results path/to/input/audio/results --o path/to/input/audio/segments
```
If you have put your files in the folder 'put-your-files-here', you can use
``` sh
python3 segments.py
```
If you use the above folder and know that you want to extract the segements at the time you run the analyis, you can use
``` sh
python3 bat_ident.py --segment on
```
and it will generate the segments to 'put-your-files-here/segments'. If you have installed the program 'sox' on your system (or sox.exe, a command line tool) and it is in your shells 'Path' variable, you can segment and generate .png images of the corresponding diagramy by using
``` sh
python3 bat_ident.py --spectrum on
```


### REST API - Online service
You can start an API service to analyze your bat calls locally or remotely. You set the area and other parameters once when you start the API service that can then answer http requests
``` sh
python3 server.py --area EU
```
e.g. using the client.py or from your remote/local application
``` sh
python3 client.py --i path/to/audio.wav
```


## References

### Papers

FROMMOLT, KARL-HEINZ. "The archive of animal sounds at the Humboldt-University of Berlin." Bioacoustics 6.4 (1996): 293-296.

Görföl, Tamás, et al. "ChiroVox: a public library of bat calls." PeerJ 10 (2022): e12445.

Gotthold, B., Khalighifar, A., Straw, B.R., and Reichert, B.E., 2022, 
Training dataset for NABat Machine Learning V1.0: U.S. Geological Survey 
data release, https://doi.org/10.5066/P969TX8F.

Kahl, Stefan, et al. "BirdNET: A deep learning solution for avian diversity monitoring." Ecological Informatics 61 (2021): 101236.

### Links

https://www.museumfuernaturkunde.berlin/en/science/animal-sound-archive

https://www.chirovox.org/

https://www.sciencebase.gov/catalog/item/627ed4b2d34e3bef0c9a2f30

https://github.com/kahst/BirdNET-Analyzer

https://xeno-canto.org/




