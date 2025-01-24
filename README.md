# Mass Codec Converter

Python scripts for batch video codec conversion with no user input required after starting. Supports long-running sessions, tracks progress, 
and allows stopping and restarting without losing much progress. Ideal for converting many files over hours or days, with ease.


## Prerequisites

- Python 3.7+ installed on your system.
- FFMPEG installed and available in your system's PATH.
- Colorama Python library installed (`pip install colorama`).


## How to use

### find_files.py

This script finds all video files within a directory of the codec that you choose, and then saves each files' filepath
to the input_files_list.txt file. At the end of the file it shows how many files it found and how many gigabytes these
files are in total, to give a view on how long the conversion might take. This file can then be directly used with the
conversion script. If you wish you could add or remove entries within this file.


### convert_codec.py

This script converts the files into your new codec using FFMPEG. It reads the input_files_list.txt file and prepares to convert the
codec of all these files. 

After every file has been converted it adds the filepath to a new file completed_files.txt together with number of seconds the conversion took. This allows the user to close the program at any time they wish and their progress will have saved, meaning that the next time you start the program it will skip all the files within the completed_files.txt file and show how long those conversions took. It will then proceed with converting the next file. 

If the input_base_folder consists of subfolders rercursively the program will keep the folder structure for the output_base_folder also. This means that when you are finished you could simply combine the output base folder with the input base folder and all the files will end up in their correct subfolder.

If files of the wrong codec are found, the conversion for this file will be skipped and the filepath of it will be saved in wrong_codec_files.txt. The script will then continue with the next file.

If there is an error with the conversion of a file, that file will be skipped and the filepath will be saved into error_files.txt. The script will then continue with the next file. 

When the script has finished processing all files it will show a summary in the terminal. If any files have failed it will be mentioned in the summary. 

Note: The script does NOT delete any files after conversion. Make sure you have free disk space for the new files.

Below is what the terminal looked like when I had finished processing all my files with the script: 

![Example Image](https://i.imgur.com/4lwGUxP.png)


### settings.cfg

- **input_base_folder:** The folder consisting of the video files you wish to convert.
- **output_base_folder:** The folder where the converted files will be saved.
- **script_folder:** Path to the folder containing the scripts, config file, and text files.

- **input_files_list_name:** The name of the file containing the filepaths.
- **use_input_files_list:** Whether to use the `input_files_list.txt` file (`True` or `False`). If false, it will convert all files in the base folder.

- **input_codec_suffix:** Codec suffix of the input files (e.g., `H265`).
- **output_codec_suffix:** Codec suffix for the converted files (e.g., `H264`).

- **speed_preset:** FFMPEG speed preset (e.g., `medium`).
- **crf_quality:** FFMPEG quality setting (e.g., `19`).

- **copy_files_of_wrong_codec:** If `True`, files with the wrong input codec are copied to the output folder.
- **verbose_information:** If `True`, more information will be showed in the terminal during the conversion. Mostly for debugging.


### Additional files

- **input_files_list.txt**: List of video files to be converted (generated by `find_files.py`).
- **completed_files.txt**: Tracks successfully converted files and their processing times.
- **wrong_codec_files.txt**: Lists files that do not match the input codec.
- **error_files.txt**: Logs files that encountered errors during conversion.

## License
This project is licensed under the [MIT License](LICENSE).
