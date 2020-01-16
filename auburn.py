#!/usr/bin/env python

# A simple script that takes audiobook files, renames them, and tags them properly

# Config file
import config as config

# For downloading audiobook cover art
from google_images_download import google_images_download
# For using the Google Book API
import requests
# For manipulating API responses
import json
# For various system commands like moving and renaming files
import os
import shutil
# For getting arguments
import argparse
# For comparing titles after Google Books API search
import sys

import Audiobook
import Author
import Library


import re

__author__ = "Jared Kick"
__copyright__ = "Copyright 2018, Jared Kick, All rights reserved."
__credits__ = ["Jared Kick"]
__license__ = "GPL"
__version__ = "0.0.3"
__maintainer__ = "Jared Kick"
__email__ = "jaredkick@gmail.com"
__status__ = "Prototype"

# TODO: ADD DATABASE FUNCTIONALITY

# TODO: ADD THREADS: USER INPUT, DOWNLOADING IMAGES, MOVING AND WRITING TAGS TO FILES

parser = argparse.ArgumentParser(description="Import audiobooks in directory or file.")
parser.add_argument("input")

# Flag to delete original audio file
parser.add_argument("-d", "--delete", help="Delete original audio file after importing.", action="store_true")

# Flag to search recursively through directory
parser.add_argument("-r", "--recursive", help="Recurse down through given directories.", action="store_true")

# Flag to print status lines
parser.add_argument("-v", "--verbose", help="Increase output verbosity.", action="store_true")

# Flag to not move or change files
parser.add_argument("-u", "--dry-run", help="Do not move or edit files.", action="store_true")

# Parse all arguments
args = parser.parse_args()

# Colors used for terminal output
class colors:
    HEADER =    '\033[95m'
    OKBLUE =    '\033[94m'
    OKGREEN =   '\033[92m'
    WARNING =   '\033[93m'
    FAIL =      '\033[91m'
    ENDC =      '\033[0m'
    BOLD =      '\033[1m'
    UNDERLINE = '\033[4m'
    RESET =     '\033[0;0m'


# Takes a search term and returns path to resulting image
def get_image(search_term):
    response = google_images_download.googleimagesdownload()
    arguments = {"keywords":search_term.replace(',', ''),
                 "limit":1,
                 "aspect_ratio":"square",
                 "no_directory":True,
                 "silent_mode":True}
    paths = response.download(arguments)
#    print(paths)
#    return paths[search_term][0]
    if paths[0][search_term.replace(',', '')][0]:
        return paths[0][search_term.replace(',', '')][0]
    else:
        return


# Used to find similarity between filename and results from Google Books API
def jaccard_similarity(list1, list2):
    s1 = set(list1)
    s2 = set(list2)
    return len(s1.intersection(s2)) / len(s1.union(s2))


def main():

    # TODO: CHECK CONFIG AND ARGUMENTS

    library = Library.Library(config.AUDIOBOOK_DIR)

    # This is the list of directories that we will look through
    # If recursive flag is there, we will add directories to this list
    files = [args.input]

    # Iterate through directory
    for audio_file in files:

        # If file is directory...
        if os.path.isdir(audio_file):
            # Add sub files and directories to list iff recursive flag is on
            if config.RECURSE or args.recursive:
                # If file is actually a subdirectory, add every content to files to be processed
                files.extend(os.listdir(audio_file))
        else:
            # Create object that we will be working with
            # TODO: THIS PROBABLY WON'T WORK WITH SUB-DIRECTORIES
            book = Audiobook.Audiobook(os.path.join(args.input, audio_file))

            # Get book information
            if args.verbose:
                print("Getting book information...")
            book.get_info()

            # Before we try to input the book, we need to make sure its
            # a valid file and not just some .txt file as well as make
            # sure this is not a dry run test.
            if book.is_valid and not args.dry_run:
                # Move to audiobook directory
                library.add_book(book)


if __name__ == "__main__":
    main()
