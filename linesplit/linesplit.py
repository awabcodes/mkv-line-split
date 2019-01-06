from tqdm import tqdm
import pysubs2
from operator import itemgetter
import subprocess
import re
import argparse
import json
import sys
import os

# Global parser namespace
cli_args = None

class Line(object):
    def __init__(self, name, start_timestamp, end_timestamp, subtitle_dialogue):
        self.name = name
        self.start_timestamp = "{}:{}:{}.{}".format(start_timestamp[0], start_timestamp[1], start_timestamp[2], start_timestamp[3],)
        self.end_timestamp = "{}:{}:{}.{}".format(end_timestamp[0], end_timestamp[1], end_timestamp[2], end_timestamp[3],)
        self.subtitle_dialogue = subtitle_dialogue

    def __str__(self):
        return "Line {}-{} ++ {}".format(self.start_timestamp, self.end_timestamp, self.subtitle_dialogue)

def parsing_lines_from_subs(mkv_obj):
    subs_path = os.path.join(mkv_obj.dirpath, mkv_obj.filename) + ".srt"

    lines = []
    subs = pysubs2.load(subs_path, encoding="utf-8")
    for line in subs:
        line_obj = Line(line.name, pysubs2.time.ms_to_times(line.start), pysubs2.time.ms_to_times(line.end), line.plaintext)
        lines.append(line_obj)

    return lines

def remove_files(mkv_obj):
    subs = os.path.join(mkv_obj.dirpath, mkv_obj.filename) + ".srt"
    audio = os.path.join(mkv_obj.dirpath, mkv_obj.filename) + ".wav"

    if os.path.exists(subs):
        os.remove(subs)
    
    if os.path.exists(audio):
        os.remove(audio)

def catch_interrupt(func):
    """Decorator to catch Keyboard Interrupts and silently exit."""
    def wrapper(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except KeyboardInterrupt:  # pragma: no cover
            pass

    # The function been catched
    return wrapper

def walk_directory(path):
    """
    Walk through the given directory to find all mkv files and process them.

    :param str path: Path to Directory containing mkv files.

    :return: List of processed mkv files.
    :rtype: list[str]
    """
    video_list = []
    if os.path.isfile(path):
        if path.lower().endswith(".mkv"):
            video_list.append(path)
        else:
            raise ValueError("Given file is not a valid mkv file: '%s'" % path)

    elif os.path.isdir(path):
        dirs = []
        # Walk through the directory
        for dirpath, _, filenames in os.walk(path):
            files = []
            for filename in filenames:
                if filename.lower().endswith(".mkv"):
                    files.append(filename)

            # Sort list of files and add to directory list
            dirs.append((dirpath, sorted(files)))

        # Sort the list of directorys & files and process them
        for dirpath, filenames in sorted(dirs, key=itemgetter(0)):
            for filename in filenames:
                fullpath = os.path.join(dirpath, filename)
                video_list.append(fullpath)
    else:
        raise FileNotFoundError("[Errno 2] No such file or directory: '%s'" % path)

    return video_list

class RealPath(argparse.Action):
    """
    Custom action to convert given path to a full canonical path,
    eliminating any symbolic links if encountered.
    """
    def __call__(self, _, namespace, value, option_string=None):
        setattr(namespace, self.dest, os.path.realpath(value))

class Track(object):
    def __init__(self, track_data):
        self.lang = track_data["properties"].get("language", "und")
        self.default_track = track_data["properties"].get("default_track")
        self.codec = track_data["codec"]
        self.type = track_data["type"]
        self.id = track_data["id"]

    def __str__(self):
        return "Track #{}: {} - {} - {}".format(self.id, self.default_track, self.lang, self.codec)

class MKVFile(object):
    def __init__(self, path):
        self.dirpath, self.filename = os.path.split(path)
        self.filename_without_extension, self.file_extension = os.path.splitext(self.filename)
        self.subtitle_tracks = []
        self.video_tracks = []
        self.audio_tracks = []
        self.path = path

        # Commandline arguments for extracting info about the mkv file
        command = [cli_args.mkvmerge_bin, "-i", "-F", "json", path]

        # Ask mkvmerge for the json info
        process = subprocess.Popen(command, stdout=subprocess.PIPE)
        stdout, _ = process.communicate(timeout=10)
        if process.returncode:
            raise RuntimeError("[Error {}] mkvmerge failed to identify: {}".format(process.returncode, self.filename))

        # Process the json response
        json__data = json.loads(stdout)
        track_map = {"video": self.video_tracks, "audio": self.audio_tracks, "subtitles": self.subtitle_tracks}
        for track_data in json__data["tracks"]:
            if track_data["properties"].get("default_track"):
                track_obj = Track(track_data)
                track_map[track_obj.type].append(track_obj)

    def extract_audio_and_subs(self):
        print("Extracting audio and subtitle")

        source_path = os.path.join(self.dirpath, self.filename)
        audio_output = os.path.join(self.dirpath, self.filename) + ".wav"
        subs_output = os.path.join(self.dirpath, self.filename) + ".srt"

        audio_track_id = str(self.audio_tracks[0].id)
        subs_track_id = str(self.subtitle_tracks[0].id)

        # Commandline arguments for extracting audio and subtitles from the mkv file
        command = [cli_args.mkvextract_bin, source_path, "tracks", audio_track_id + ":" + audio_output , subs_track_id + ":" + subs_output]

        # Ask mkvextract to do the extracting command
        process = subprocess.Popen(command, stdout=subprocess.PIPE)
        stdout, _ = process.communicate(timeout=10)
        if process.returncode:
            raise RuntimeError("[Error {}] mkvextract failed to extract: {}".format(process.returncode, self.filename))
        
    def split_lines(self, lines):
        print("Spliting voice lines, Please wait...")

        for line in tqdm(lines):
            source_path = os.path.join(self.dirpath, self.filename) + ".wav"

            # check whether their is a name for the dialogue
            if line.name:
                output_path = os.path.join(self.dirpath, self.filename_without_extension, line.name, line.subtitle_dialogue) + ".wav"
            else:
                output_path = os.path.join(self.dirpath, self.filename_without_extension, "noname", line.subtitle_dialogue) + ".wav"

            # Commandline arguments for splitting audio from the mkv audio
            command = [cli_args.mkvmerge_bin, source_path, "-o", output_path, "--split", "parts:" + line.start_timestamp + "-" + line.end_timestamp]

            # Ask mkvmerge to do the splitting command
            process = subprocess.Popen(command, stdout=subprocess.PIPE)
            stdout, _ = process.communicate(timeout=10)

            if process.returncode:
                continue
                # raise RuntimeError("[Error {}] mkvmerge failed to split lines: {}".format(process.returncode, self.filename))
            
        # remove the extracted files
        remove_files(self)

        print("==== Finished!! ====")
    
@catch_interrupt
def main(params=None):
    parser = argparse.ArgumentParser(description="Strips lines according to timestamps.")
    parser.add_argument("path", action=RealPath, metavar="mkv-path",
                        help="Where your MKV files are stored. Can be a directory or a file.")
    parser.add_argument("-m", "--mkvmerge-bin", action="store", metavar="mkvmerge-path", required=True,
                        help="The path to the MKVMerge executable.")
    parser.add_argument("-x", "--mkvextract-bin", action="store", metavar="mkvextract-path", required=True,
                        help="The path to the MKVExtract executable.")

    # Parse the list of given arguments
    globals()["cli_args"] = parser.parse_args(params)

    # Iterate over all found mkv files
    print("==== Searching for MKV files to process. ====")

    for mkv_file in walk_directory(cli_args.path):
        mkv_obj = MKVFile(mkv_file)
        print("Found: {}".format(mkv_obj.filename))
        mkv_obj.extract_audio_and_subs()
        lines = parsing_lines_from_subs(mkv_obj)
        mkv_obj.split_lines(lines)


if __name__ == "__main__":
    main()