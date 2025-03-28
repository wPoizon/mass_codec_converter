import os
import subprocess
import sys
import time
import configparser
import shutil
from colorama import Fore, Style
from colorama import init
init(autoreset=True)

# Get path to settings.cfg file
config = configparser.ConfigParser()
script_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(script_dir, 'settings.cfg')
config.read(config_path)

# Access variables in the Paths section
input_base_folder = config.get('Paths', 'input_base_folder')
input_base_folder = os.path.abspath(input_base_folder)
output_base_folder = config.get('Paths', 'output_base_folder')
output_base_folder = os.path.abspath(output_base_folder)
script_folder = config.get('Paths', 'script_folder')
input_files_list_name = config.get('Paths', 'input_files_list_name')
use_input_files_list = config.getboolean('Paths', 'use_input_files_list')

# Access variables in the Codecs section
input_codec = config.get('Codecs', 'input_codec')
skip_codec_checking = config.getboolean('Codecs', 'skip_codec_checking')
encoder = config.get('Codecs', 'encoder')

# Access variables in the Transcoding settings section
speed_preset = config.get('Transcoding settings', 'speed_preset')
crf_quality = config.get('Transcoding settings', 'crf_quality')

# Access variables in the Other settings section
copy_files_of_wrong_codec = config.getboolean('Other', 'copy_files_of_wrong_codec')
verbose_information = config.getboolean('Other', 'verbose_information')

use_different_extension = config.getboolean('Other', 'use_different_extension')
output_extension = config.get('Other', 'output_extension')

if (verbose_information):
    loglevel = "verbose"
else:
    loglevel = "error"

# Set paths
files_list_path = os.path.join(script_folder, input_files_list_name)
completed_files_path = os.path.join(script_folder, "completed_files.txt")
error_files_path = os.path.join(script_folder, "error_files.txt")
wrong_codec_files_path = os.path.join(script_folder, "wrong_codec_files.txt")

video_extensions = (".mp4", ".mkv", ".avi", ".mov", ".flv", ".wmv")

# Adjust encoder for FFMPEG
encoder = encoder.strip().lower()
encoder_mapping = {
    "x264": "libx264",
    "x264_nvenc": "h264_nvenc",
    "x265": "libx265",
    "x265_nvenc": "h265_nvenc"
}
ffmpeg_encoder = encoder_mapping.get(encoder)
if ffmpeg_encoder is None:
    print("Error: Invalid encoder specified in settings.cfg. Exiting.")
    sys.exit()

# Adjust input codec for FFMPEG
input_codec = input_codec.strip().lower()
codec_mapping = {
    "h264" : "h264",
    "h265" : "hevc",
    "vp9" : "vp9",
}
ffmpeg_input_codec = codec_mapping.get(input_codec)
if ffmpeg_input_codec is None:
    print("Error: Invalid input codec specified in settings.cfg. Exiting.")
    sys.exit()

encoding_speed_list = {
    "ultrafast",
    "superfast",
    "veryfast",
    "faster",
    "fast",
    "medium",
    "slow",
    "slower",
    "veryslow",
    "placebo"
}

if (speed_preset not in encoding_speed_list):
    print("Error: Invalid speed_preset specified in settings.cfg. Exiting.")
    sys.exit()

try:
    crf_quality_int = int(crf_quality)  # Convert to integer before validation
    if crf_quality_int < 0 or crf_quality_int > 51:  # Validate range
        print("Error: Invalid crf_quality specified in settings.cfg. Exiting.")
        sys.exit()
except ValueError:  # Handle non-integer values
    print("Error: crf_quality must be an integer in settings.cfg. Exiting.")
    sys.exit()

# Initialize counters
success_counter = 0
failed_counter = 0
wrong_codec_counter = 0
total_files = 0

total_seconds = 0

def rgb_color(r, g, b):
    return f"\033[38;2;{r};{g};{b}m"

shades_of_yellow = [
    rgb_color(255, 135, 100),  # Light yellow
    rgb_color(255, 170, 100),  # Medium yellow
    rgb_color(255, 200, 100),   # Darker yellow
    rgb_color(255, 255, 100)    # Even darker yellow
]

def format_seconds_dynamically(total_seconds):
    days, remainder = divmod(total_seconds, 86400)  # 86400 seconds in a day
    hours, remainder = divmod(remainder, 3600)     # 3600 seconds in an hour
    minutes, seconds = divmod(remainder, 60)      # 60 seconds in a minute

    # Dynamically build the time string
    time_parts = []
    if days > 0:
        time_parts.append(f"{shades_of_yellow[0]}{days} days{Style.RESET_ALL}")
    if hours > 0:
        time_parts.append(f"{shades_of_yellow[1]}{hours} hours{Style.RESET_ALL}")
    if minutes > 0:
        time_parts.append(f"{shades_of_yellow[2]}{minutes} minutes{Style.RESET_ALL}")
    if seconds > 0 or not time_parts:  # Include seconds if it's the only unit
        time_parts.append(f"{shades_of_yellow[3]}{seconds} seconds{Style.RESET_ALL}")
    
    return ", ".join(time_parts)

def format_file_size(file_path):
    """Return the size of a file in a readable format."""
    size_in_bytes = os.path.getsize(file_path)
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_in_bytes < 1024:
            return f"{size_in_bytes:.2f} {unit}"
        size_in_bytes /= 1024

# Load the list of completed files and their times
completed_files = set()
if os.path.exists(completed_files_path):
    with open(completed_files_path, "r", encoding="utf-8") as cf:
        for line in cf:
            if line.strip():  # Ensure the line is not empty
                try:
                    # Split the line into time and file path
                    seconds, file_path = line.split(" ", 1)
                    if (seconds == "copied"):
                        pass
                    else: 
                        total_seconds += int(seconds)  # Add the time to total_time
                    completed_files.add((file_path.strip(), seconds))  # Add file path and the time it took to the set
                except ValueError:
                    print(f"Skipping malformed line in {completed_files_path}: {line.strip()}")
                    sys.exit()
    
# Load the list of error files
if os.path.exists(error_files_path):
    with open(error_files_path, "r", encoding="utf-8") as cf:
        error_files = set(line.strip() for line in cf if line.strip())
else:
    error_files = set()
        
# Load the list of wrong codec files
if os.path.exists(wrong_codec_files_path):
    with open(wrong_codec_files_path, "r", encoding="utf-8") as cf:
        other_codec_files = set(line.strip() for line in cf if line.strip())
else:
    other_codec_files = set()

# Read the list of input files
if (use_input_files_list):
    with open(files_list_path, "r", encoding="utf-8") as f:
        input_files = [line.strip() for line in f if line.strip() and not line.startswith("Total ")]
        input_files = [f for f in input_files if f.lower().endswith(video_extensions)]  # Filter non-video files
else:
    # Recursively find all video files in the input_base directory
    input_files = []
    for path_and_name, _, files in os.walk(input_base_folder):
        for file in files:
            if file.lower().endswith(video_extensions):  # Use video_extensions for filtering
                input_files.append(os.path.join(path_and_name, file))

# Count total video files
for input_file in input_files:
    if input_file.lower().endswith(video_extensions):
        total_files += 1

print()

# Process each file
for input_file in input_files:
    # Construct the output file path
    try:
        relative_path = os.path.relpath(input_file, input_base_folder)
    except ValueError as e:
        print(Fore.RED + f"Error constructing relative path for {input_file}: {e}" + Style.RESET_ALL)
        failed_counter += 1
        if not any(input_file in error for error in error_files):
            with open(error_files_path, "a", encoding="utf-8") as cf:
                cf.write(f"Error constructing relative path: {input_file}\n")
            error_files.add(f"Error constructing relative path: {input_file}")
        continue
    
    output_file = os.path.join(output_base_folder, relative_path)
    
    bit_depth = "8bit" if ffmpeg_encoder in ["libx264", "h264_nvenc"] else "10bit"  
    path_and_name, original_extension = os.path.splitext(output_file)
    
    if use_different_extension:
        output_file = f"{path_and_name}.{output_extension}"

    matching_tuple = None

    # Iterate through the completed_files set
    for completed in completed_files:
        if output_file == completed[0]:  # Check if the file matches
            matching_tuple = completed   # Save the matching tuple
            break                        # Exit the loop once a match is found

    # Skip if the file is already marked as completed
    if matching_tuple:
        if (matching_tuple[1] != "copied"):
            success_counter += 1
            print(Fore.CYAN + f"{success_counter+wrong_codec_counter+failed_counter}. File already transcoded ({format_seconds_dynamically(int(matching_tuple[1]))}" + Fore.CYAN + f"): {output_file}" + Style.RESET_ALL, sep="")
        else:
            wrong_codec_counter += 1
            print(Fore.CYAN + f"{success_counter+wrong_codec_counter+failed_counter}. File already copied: " + Fore.CYAN + f"{output_file}" + Style.RESET_ALL, sep="")
        matching_tuple = None  # We are done using it, uninitializing it
        continue
    
    print(f"\n\n--------------------------------")
    print(f"{success_counter} files successfully transcoded")
    print(f"{Fore.RED if failed_counter > 0 else Style.RESET_ALL}{failed_counter} files failed{Style.RESET_ALL}")
    print(f"{Fore.MAGENTA if wrong_codec_counter > 0 else Style.RESET_ALL}{wrong_codec_counter} files not in {input_codec} {Style.RESET_ALL}", end="")
    if ((copy_files_of_wrong_codec)):
        print("(Copied)")
    else:
        print("")
    print(f"{total_files-success_counter-failed_counter-wrong_codec_counter} files left to transcode")
    print(f"{total_files} files total")
    print(f"--------------------------------\n\n")

    # Get the codec of the file
    try:
        ffprobe_cmd = [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=codec_name,profile,pix_fmt", "-of", "default=noprint_wrappers=1:nokey=1", input_file
        ]
        output = subprocess.check_output(ffprobe_cmd, text=True).strip().split("\n")

        # Assign correct values
        input_codec_name = output[0].strip().replace(".", "").replace("-", "").lower() if len(output) > 0 else "unknown"
        input_profile = output[1] if len(output) > 1 else "Unknown"
        input_pixel_format = output[2] if len(output) > 2 else "Unknown"

        print(f"Detected Codec: {input_codec_name}, Profile: {input_profile}, Pixel Format: {input_pixel_format}")
    except subprocess.CalledProcessError:
        print(Fore.RED + f"Error reading codec for {input_file}. Skipping." + Style.RESET_ALL)
        input_codec_name, input_profile, input_pixel_format = "Unknown", "Unknown", "Unknown"
        failed_counter += 1
        
        if not any(input_file in error for error in error_files):
            with open(error_files_path, "a", encoding="utf-8") as cf:
                cf.write(f"Error reading codec: {input_file}\n")
            error_files.add(f"Error reading codec: {input_file}")
        continue

    # If file is the right codec, start transcoding process
    if input_codec_name.lower() == ffmpeg_input_codec.lower() or skip_codec_checking:
        
        # Ensure the output directory exists
        output_dir = os.path.dirname(output_file)
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
            except OSError as e:
                print(Fore.RED + f"Failed to create directory {output_dir}: {e}" + Style.RESET_ALL)
                failed_counter += 1
                
                if not any(output_dir in error for error in error_files):
                    with open(error_files_path, "a", encoding="utf-8") as cf:
                        cf.write(f"Error creating directory: {output_dir}\n")
                    error_files.add(f"Error creating directory: {output_dir}")
                continue
            print(Fore.YELLOW + f"Created directory: {output_dir}" + Style.RESET_ALL)
        
        # Printout of what file is going to be transcoded
        print(
            Fore.GREEN + f"Starting transcoding process of a "
            + f"{Fore.RED}{format_file_size(input_file)}"
            + f"{Fore.GREEN} file: "
            + f"\n\n\t{Fore.CYAN}{input_file}"
            + f"{Fore.GREEN}\n" + Style.RESET_ALL
        )
        
        
        # Ensure correct bit depth
        if ffmpeg_encoder in ["libx264", "h264_nvenc"]:
            pixel_format = "yuv420p"  # Forces 8-bit
        elif ffmpeg_encoder in ["libx265", "h265_nvenc"]:
            pixel_format = "yuv420p10le"  # Forces 10-bit
        else:
            print("Error: Unknown encoder. Skipping.")
            continue



        # FFMPEG transcoding command
        ffmpeg_cmd = [
            "ffmpeg", "-y", "-i", input_file, "-map", "0",  
            "-c:v", ffmpeg_encoder, "-crf", crf_quality, "-preset", speed_preset,
            "-pix_fmt", pixel_format,  # Explicitly enforce bit depth
            "-c:a", "copy",  # Copy the audio without re-encoding
            "-c:s", "copy",  # Copy subtitles
            "-loglevel", loglevel,  # Show only errors
            "-hide_banner",  # Suppress extra details
            "-stats",  # Show encoding stats
            output_file
        ]


    
        # Transcode!
        try:
            # Start a timer
            start_time = time.time()
            
            # Transcoding command
            subprocess.run(ffmpeg_cmd, check=True)
            
            # Stop timer
            transcoding_time = int(time.time() - start_time)
            
            # Mark as completed
            with open(completed_files_path, "a", encoding="utf-8") as cf:
                cf.write(f"{transcoding_time} {output_file} \n")
            
            # Increment the counter
            success_counter += 1
            total_seconds += transcoding_time
            
            print(
                Fore.GREEN + f"\n{output_file}\n"
                + Fore.CYAN + "Successfully finished transcoding! \n"
                + Fore.YELLOW + f"File took {format_seconds_dynamically(transcoding_time)}{Fore.YELLOW} to transcode. "
                + Style.RESET_ALL
            )
              
        # Transcoding failed...  
        except subprocess.CalledProcessError:
            print(Fore.RED + f"Error transcoding {input_file}. Skipping." + Style.RESET_ALL)
            failed_counter += 1
            
            if not any(input_file in error for error in error_files):
                with open(error_files_path, "a", encoding="utf-8") as cf:
                    cf.write(f"Error while transcoding: {input_file}\n")
                error_files.add(f"Error while transcoding: {input_file}")
            continue
    else:
        print(Fore.MAGENTA + f"File is not {input_codec}:\n\n\t{Fore.CYAN}{input_file}" + Style.RESET_ALL)
        wrong_codec_counter += 1
        
        if (copy_files_of_wrong_codec):
            
            print(f"{Fore.YELLOW}\nCopying... {Style.RESET_ALL}")
            
            # Construct the output path
            relative_path = os.path.relpath(input_file, input_base_folder)  # Get relative path from input_base
            output_path = os.path.join(output_base_folder, relative_path)

            # Ensure the output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            try:
                # Check if the file exists
                if os.path.exists(output_path):
                    os.remove(output_path)  # Remove the file if it exists
                
                # Copy the file
                shutil.copy(input_file, output_path)
                
            except PermissionError as e:
                print(f"Permission denied while copying {input_file} to {output_path}. Error: {e}")

            except Exception as e:
                print(f"An unexpected error occurred while copying {input_file} to {output_path}. Error: {e}")
                
            
            # Mark as completed
            with open(completed_files_path, "a", encoding="utf-8") as cf:
                cf.write(f"copied {output_path}\n")
        
        if not any(input_file in error for error in other_codec_files):
            with open(wrong_codec_files_path, "a", encoding="utf-8") as cf:
                cf.write(f"File is {input_codec_name}, not {ffmpeg_input_codec}: " + output_file + " \n")
            other_codec_files.add(f"File is {input_codec_name}, not {ffmpeg_input_codec}: {output_file}")

print(Fore.BLUE + "\n\nSUMMARY:\n" + Style.RESET_ALL)
print(Fore.GREEN + f"Successfully transcoded: {success_counter}" + Style.RESET_ALL)
print(Fore.GREEN + f"Wrong codec: {Fore.RED}{wrong_codec_counter}" + Style.RESET_ALL)
print(Fore.GREEN + f"Failed transcodings: {Fore.RED}{failed_counter}" + Style.RESET_ALL)
print(Fore.GREEN + f"Total number of files handled: {total_files}" + Style.RESET_ALL)
print(Fore.GREEN + f"Total time elapsed: {format_seconds_dynamically(total_seconds)}" + Style.RESET_ALL)
print(Fore.BLUE + f"\nFINISHED PROCESSING ALL FILES\n" + Style.RESET_ALL)