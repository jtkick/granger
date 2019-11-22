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


class Library:
    base_dir = ""

    def __init__(self):
        pass

    def __init__(self, library_dir):
        if (os.path.isdir(library_dir)):
            self.base_dir = library_dir
        else:
            raise NotADirectoryError(library_dir + ": not a valid directory")

    # This function moves the audiobook and cover to pre-specified library location
    # This should not be called until tags have been written, and a cover has
    # been found and downloaded
    def add_book(self, book):
        #if (book is not Audiobook):
        #    raise TypeError("Illegal type: Expecting Audiobook")

        new_location = os.path.join(self.base_dir, book.author)

        # TODO: Add author the proper way, then add book to author
        # If directory doesn't exist, make one
        if not os.path.isdir(new_location):
            self.add_author(book.author)

        new_location = os.path.join(new_location, book.title)

        # Make sure title directory exists
        if not os.path.isdir(new_location):
            os.mkdir(new_location)

        # Get audio file extension
        file_extension = os.path.splitext(book.audio_location)[-1]

        new_location = os.path.join(new_location, (book.title + file_extension))

        # Move audio file
        if os.path.isfile(new_location):
            # If the book already exists in the library, do one of the following
            if config.OVERWRITE == "bitrate":
                old_file = mutagen.File(new_location)
                new_file = mutagen.File(book.audio_location)
                # If new file's bitrate is higher, remove the old file
                if new_file.info.bitrate > old_file.info.bitrate:
                    # Remove old file and add new file
                    os.remove(new_location)
                    shutil.copy2(book.audio_location, new_location)
            elif config.OVERWRITE == "size":
                # If new file is bigger, remove the old file
                if os.path.getsize(book.audio_location) > os.path.getsize(new_location):
                    # Remove old file and add new file
                    os.remove(new_location)
                    shutil.copy2(book.audio_location, new_location)
            elif config.OVERWRITE == "always":
                # Remove old file and add new file
                os.remove(new_location)
                shutil.copy2(book.audio_location, new_location)
            elif config.OVERWRITE != "never":
                print("Invalid value for \"OVERWRITE\" in configuration file.")
                raise ValueError
        else:
            # If theres nothing there, just copy it
            shutil.copy2(book.audio_location, new_location)

        # Delete audio file
        if config.DELETE or args.delete:
            os.remove(book.audio_location)

        # Update location in class regardless
        book.audio_location = new_location

        # Get image file extension
        file_extension = os.path.splitext(book.image_location)[1]

        # Set new location of image file
        new_location = os.path.join(self.base_dir,
                                    book.author,
                                    book.title,
                                    ("folder" + file_extension))

        # Move and rename file to "folder" with the original extension
        if os.path.isfile(new_location):
            os.remove(new_location)
        os.rename(book.image_location, new_location)

        # Update book image location
        book.image_location = new_location
    
    def add_author(self, author):
        new_location = os.path.join(self.base_dir, author)
        if (os.path.isdir(new_location)):
            return
        else:
            os.mkdir(new_location)

            # Get author image
            image_location = get_image("\"" + author + "\" author")

            # Get file extension
            file_extension = os.path.splitext(image_location)[-1]

            # All images are named 'folder'
            new_location = os.path.join(new_location, ("folder" + file_extension))

            # Move image to library author directory
            os.rename(image_location, new_location)


def main():

    # TODO: CHECK CONFIG AND ARGUMENTS

    library = Library(config.AUDIOBOOK_DIR)

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
            book = Audiobook(os.path.join(args.input, audio_file))

            # Get book information
            if args.verbose:
                print("Getting book information...")
            book.get_info()

            # Before we try to input the book, we need to make sure its
            # a valid file and not just some .txt file as well as make
            # sure this is not a dry run test.
            if book.is_valid and not args.dry_run:
                # Get cover image
                if args.verbose:
                    print("Downloading book cover...")
                book.get_cover()

                # Write info to audio file
                if args.verbose:
                    print("Writing audio file tags...")
                book.write_tags()

                # Move to audiobook directory
                library.add_book(book)


if __name__ == "__main__":
    main()
