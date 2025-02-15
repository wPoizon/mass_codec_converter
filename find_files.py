import os
import configparser
import subprocess
import sys

# Get path to settings.cfg file
config = configparser.ConfigParser()
script_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(script_dir, 'settings.cfg')
config.read(config_path)

# Access variables in the Paths section
input_base_folder = config.get('Paths', 'input_base_folder')
script_folder = config.get('Paths', 'script_folder')
input_files_list_name = config.get('Paths', 'input_files_list_name')
input_codec = config.get('Codecs', 'input_codec').strip().lower()

# Set paths
files_list_path = os.path.join(script_folder, input_files_list_name)

# Adjust input codec for FFMPEG
codec_mapping = {
    "h264" : "h264",
    "h265" : "hevc",
    "vp9" : "vp9",
}
ffmpeg_input_codec = codec_mapping.get(input_codec)
if ffmpeg_input_codec is None:
    print("Error: Invalid input codec specified in settings.cfg. Exiting.")
    sys.exit()

def is_codec(codec, file_path):
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=codec_name", "-of", "default=nw=1:nk=1", file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10  # Timeout in seconds
        )
        return result.stdout.strip() == codec  # Direct codec comparison
    except subprocess.TimeoutExpired:
        print(f"Timeout checking file {file_path}. Skipping...")
        return False
    except Exception as e:
        print(f"Error checking file {file_path}: {e}")
        return False


def find_codec_videos(codec, input_base, output_file):
    current_folder = None
    total_files = 0
    total_size_gb = 0.0

    # Ensure the output file is empty before starting
    open(output_file, 'w', encoding='utf-8').close()

    for root, _, files in os.walk(input_base):
        folder_size = 0  # Size of H265 files in the current folder (in bytes)
        for name in files:
            file_path = os.path.join(root, name)
            print(f"Checking file: {file_path}")
            if is_codec(ffmpeg_input_codec, file_path):
                total_files += 1
                # Get the file size in bytes
                file_size = os.path.getsize(file_path)
                folder_size += file_size
                total_size_gb += file_size / (1024 ** 3)  # Convert bytes to GB
                if current_folder != root:
                    with open(output_file, 'a', encoding='utf-8') as file:
                        if current_folder is not None:  # Avoid adding an empty line before the first folder
                            file.write("\n")
                    current_folder = root
                    print(f"Found {codec} files in folder: {current_folder}")
                
                # Write directly to the output file
                with open(output_file, 'a', encoding='utf-8') as file:
                    file.write(f"{file_path}\n")
                print(f"   Found {codec} file: {name} ({file_size / (1024 ** 3):.2f} GB)\n")

        if folder_size > 0:
            folder_size_gb = folder_size / (1024 ** 3)  # Convert folder size to GB
            print(f"Total size in folder '{root}': {folder_size_gb:.2f} GB")

    # Write final summary to the output file
    with open(output_file, 'a', encoding='utf-8') as file:
        file.write(f"\nTotal {codec} files: {total_files}\n")
        file.write(f"Total size: {total_size_gb:.2f} GB\n")

    print(f"\nCompleted! Found {total_files} {codec} files.")
    print(f"Total size of all {codec} files: {total_size_gb:.2f} GB")

print("input_files_list_name: " + input_files_list_name)
print("files_list_path: " + files_list_path)

find_codec_videos(ffmpeg_input_codec, input_base_folder, files_list_path)
