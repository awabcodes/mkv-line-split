# mkv-line-split

> mkv-linesplit is a Python script for splitting or cutting audio segments from mkv files.

> First it extracts the audio and subtitles from the mkv file, Then it splits the lines from the audio file according to the timestamps stored in the subtitles and names the output file to the corresponding line.

---

## Requirements

1. [Python3](https://www.python.org/downloads/)
2. [MKVToolNix](https://mkvtoolnix.download/downloads.html)

> **mkvextract** used for extracting the audio and subtitle from the mkv file.

> **mkvmerge** used for splitting the parts from the mkv audio.

---

## Installation
    $ pip install mkv-line-split

---

## Usage

    $ linesplit -m path/to/mkvmerge -x path/to/mkvextract path/to/mkv/file/or/directory
