import os
import configparser
import subprocess
import sys

# Load the configuration file
config = configparser.ConfigParser()
config.read('settings.cfg')  # Update to the actual location of your properties file


script_folder = config.get('Paths', 'script_folder')
input_base_folder = config.get('Paths', 'input_base_folder')
input_files_list_name = config.get('Paths', 'input_files_list_name')
input_codec_suffix = config.get('Codecs', 'input_codec_suffix')

# Set paths
log_and_input_files_path = script_folder + "\\"  # Path to your files.txt
files_list_path = log_and_input_files_path + input_files_list_name  # Path to your files.txt

if (input_codec_suffix == "H264"):
    input_suffix = "libx264"
elif (input_codec_suffix == "H265"):
    input_suffix = "hevc"
else:
    print("Wrong codec, exiting")
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
        return result.stdout.strip() == codec  # 'hevc' is the codec name for H265
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
            if is_codec(codec, file_path):
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
                print(f"   Found {codec} file: {name} ({file_size / (1024 ** 3):.2f} GB)")

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

find_codec_videos(input_suffix, input_base_folder, files_list_path)
