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


# This is what we are going to use to build our new audiobook file
class Audiobook:
    title = ""
    subtitle = ""
    author = ""
    publisher = ""
    genre = ""
    year = ""
    description = ""
    is_excerpt = False
    is_valid = False

    # Keep track of the current absolute path of the audiobook file and
    # it's corresponding cover file
    audio_location = ""
    image_location = ""
    
    def __init__(self):
        self.title = ""
        self.subtitle = ""
        self.author = ""
        self.publisher = ""
        self.genre = ""
        self.year = ""
        self.description = ""
        self.is_excerpt = False
        self.audio_location = ""
        self.image_location = ""

    def __init__(self, location):
        self.title = ""
        self.subtitle = ""
        self.author = ""
        self.publisher = ""
        self.genre = ""
        self.year = ""
        self.description = ""
        self.is_excerpt = False
        self.audio_location = location
        self.image_location = ""

    # Print audiobook, mostly for debugging and testing purposes
    def __str__(self):
        return("Title:       " + self.title + "\n" + 
               "Subtitle:    " + self.subtitle + "\n" +
               "Author:      " + self.author + "\n" +
               "Publisher:   " + self.publisher + "\n" +
               "Year:        " + self.year + "\n" +
               "Description: " + self.description + "\n" +
               "Audio Loc.:  " + self.audio_location + "\n" +
               "Image Loc.:  " + self.image_location)

    # Writes tags to audio file 'self'
    # Path to the audio file should be passed to the function
    def write_tags(self):
        # Assume it's .ogg for now, add more functionality when this works properly
        audio_file = mutagen.File(self.audio_location)

        audio_file["TITLE"] = self.title
        audio_file["ALBUM"] = self.title
        audio_file["ARTIST"] = self.author
        audio_file["PRODUCER"] = self.publisher
        audio_file["DATE"] = self.year
        audio_file["DESCRIPTION"] = self.description
        
        audio_file.save()

    # Get a cover image for the audiobook
    def get_cover(self):
        self.image_location = get_image("\"" + self.author + " " + self.title + " audiobook\"")
    
    # Search Google Books API for information about book based on
    # file name and write to Audiobook object
    def get_info(self):
        # Get filename
        filename = os.path.basename(self.audio_location)
        if args.verbose:
            print("Getting info for: " + filename)

        # Split filename
        search_term, ext = os.path.splitext(filename)

        # Make sure file is valid
        if ext in config.FORMATS:
            self.is_valid = True
        else:
            if args.verbose:
                print("\"" + ext + "\" is not in valid format list. Skipping.")
            self.is_valid = False
            return

        # We will work with lowercase strings
        search_term = search_term.lower()

        # Set reminder if file is an excerpt
        if "excerpt" in search_term:
            if args.verbose:
                print("File: \"" + filename + "\" is an excerpt.")
            self.is_excerpt = True
            search_term = search_term.replace("excerpt", '')

        # Remove unhelpful words
        for word in WORDS:
            search_term = search_term.replace(word, ' ')

        # Remove special characters
        for char in SPEC_CHARS:
            search_term = search_term.replace(char, ' ')

        # TODO: HANDLE CHAPTERS
        # We'll get back to this
        # If chapter is found, it takes precedence over parts
        # i.e. 

        # TODO: HANDLE PARTS
        # Since some assholes like to format parts backwards, i.e. part one
        # of three is written 3/1, we will break it up and take the smallest

        # This loop is to make sure the user confirms the info found
        info_correct = False
        while not info_correct:
            # Search Google Books API
            if args.verbose:
                print("Sending Google Books API request...")
                print("Search term : " + search_term)
            response = requests.get("https://www.googleapis.com/books/v1/volumes?q=" +
                                search_term.replace(' ', '+'))

            # Make JSON response readable
            response = response.json()

            # Compare titles by iterating through titles and seeing which ones match original
            # While Google Books search is good, occasionally it returns books that are
            # clearly not a match, so we will crosscheck the result with the original string
            # and see which one is the closest
            match = ""
            ratio = 0.0
            if "items" in response:
                for item in response["items"]:
                    # Search using just the title and author
                    response_str = ""
                    if "title" in item["volumeInfo"]:
                        response_str += item["volumeInfo"]["title"]
                    if "authors" in item["volumeInfo"]:
                        response_str += " "
                        response_str += item["volumeInfo"]["authors"][0]
                    response_str = response_str.lower()
                    # Remove special characters
                    for char in SPEC_CHARS:
                        response_str = response_str.replace(char, ' ')
                    test_ratio = jaccard_similarity(search_term.split(), response_str.split())
                    if test_ratio > ratio:
                        match = item["volumeInfo"]
                        ratio = test_ratio

                    # Search again, but this time including the subtitle
                    response_str = ""
                    if "title" in item["volumeInfo"]:
                        response_str += item["volumeInfo"]["title"]
                    if "subtitle" in item["volumeInfo"]:
                        response_str += " " + item["volumeInfo"]["subtitle"]
                    if "authors" in item["volumeInfo"]:
                        response_str += " " + item["volumeInfo"]["authors"][0]
                    response_str = response_str.lower()
                    # Remove special characters
                    for char in SPEC_CHARS:
                        response_str = response_str.replace(char, ' ')
                    test_ratio = jaccard_similarity(search_term.split(), response_str.split())
                    if test_ratio > ratio:
                        match = item["volumeInfo"]
                        ratio = test_ratio

            # Successful search
            if ratio >= 0.5:
                # Skip user prompt if prompt level is 'never' or 'medium'
                if config.PROMPT_LEVEL == 0 or config.PROMPT_LEVEL == 1:
                    info_correct = True
            # Not quite sure
            if ratio < 0.5 and ratio >= 0.25:
                # Skip user prompt if prompt level is 'never'
                if config.PROMPT_LEVEL == 0:
                    info_correct = True
            # Bad match
            if ratio < 0.25:
                # Skip user prompt if prompt level is 'never' and throw out file
                if config.PROMPT_LEVEL == 0:
                    info_correct = True
                    self.is_valid = False
                    return

            if ratio >= 0.5:
                print(colors.OKGREEN + "Similarity: Good " +
                      colors.BOLD + "(" + "{:.0%}".format(ratio) + ")" + colors.ENDC + " ")
            elif ratio < 0.5 and ratio >= 0.25:
                print(colors.WARNING + "Similarity: Moderate " +
                      colors.BOLD + "(" + "{:.0%}".format(ratio) + ")" + colors.ENDC + " ")
            elif ratio < 0.25:
                print(colors.FAIL + "Similarity: Bad " +
                      colors.BOLD + "(" + "{:.0%}".format(ratio) + ")" + colors.ENDC + " ")

            # Display what the program found
            print(colors.OKBLUE + "Filename: " + colors.WARNING + filename)
            if "title" in match:
                print(colors.OKBLUE + "Title:    " + colors.OKGREEN + match["title"])
            if "subtitle" in match:
                print(colors.OKBLUE + "Subtitle: " + colors.OKGREEN + match["subtitle"])
            if "authors" in match:
                print(colors.OKBLUE + "Author:   " + colors.OKGREEN + match["authors"][0])

            # Prompt user if necessary
            if not info_correct:
                valid_options = ['A', 'a', 'M', 'm', 'E', 'e', 'S', 's', 'B', 'b', '']
                user_input = ""
                while (user_input not in valid_options):
                    # Prompt user for input
                    print(colors.WARNING + "Is this information correct?")
                    print(colors.WARNING + "Options: [A]pply, [M]ore Candidates, [E]nter Search, [S]kip, A[B]ort")
                    user_input = input(colors.WARNING + "Command:" + colors.RESET + " ")

                if user_input == 'A' or user_input == 'a':
                    # Exit loop and write match information
                    info_correct = True
                elif user_input == 'M' or user_input == 'm':
                    # TODO: SHOW USER ALL OTHER OPTIONS
                    pass
                elif user_input == 'E' or user_input == 'e':
                    # Do it again with new information
                    search_term = input("Title: ")
                    search_term += " " + input("Author: ")
                    search_term = search_term.lower()
                elif user_input == 'S' or user_input == 's':
                    # Drop this file and move on
                    self.is_valid = False
                    return
                elif user_input == 'B' or user_input == 'b':
                    # Pull the plug
                    sys.exit()

        # Write match info to Audiobook object
        if "title" in match:
            self.title = match["title"]
        if "subtitle" in match:
            self.subtitle = match["subtitle"]
        if "authors" in match:
            self.author = match["authors"][0]
        else:
            self.author = "Unknown Author"
        if "publisher" in match:
            self.publisher = match["publisher"]
        if "categories" in match:
            self.genre = match["categories"][0]
        if "publishedDate" in match:
            # Find four digit number
            # TODO: FIX THIS, IT IS NOT WORKING CORRECTLY. CONSIDER USING re.search() INSTEAD OF re.match()
            self.year = str(re.match(r"(?<!\d)\d{4}(?!\d)", match["publishedDate"]))
        if "description" in match:
            self.description = match["description"]


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
