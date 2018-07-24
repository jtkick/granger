#!/usr/bin/env python

# A simple script that takes audiobook files, renames them, and tags them properly

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
import Levenshtein
import re
# For reading and writing audio tags
import mutagen

__author__ = "Jared Kick"
__copyright__ = ""
__credits__ = ["Jared Kick"]
__license__ = "GPL"
__version__ = "0.0.1"
__maintainer__ = "Jared Kick"
__email__ = "jaredkick@gmail.com"
__status__ = "Prototype"

parser = argparse.ArgumentParser(description="Import audiobooks in directory.")
parser.add_argument("directory")
# Flag to delete original audio file
parser.add_argument("-d", action="store_true")
args = parser.parse_args()

# This should be in a config file
AUDIOBOOK_DIR = "/home/jared/Software/Development/Auburn/AUDIOBOOK_DIR/"

# Words to remove that tend to appear in file names but don't describe the book
# These words (especially "audiobook") tend to screw up Google Books searches
WORDS = ["audiobooks", "audiobook", "audio", "book", " by ", "narrated", "full", "complete", "hd", "pdf", "abridged", "unabridged", "subtitles", ".com", ".net", ".org", "mp3", "mp4", "m4v", "m4a", "m4b"]

# Special characters to remove from filename. '&' and ''' are NOT removed as these are sometimes helpful
SPEC_CHARS = ['~', '`', '@', '$', '%', '^', '*', '_', '=', '<', '>', '(', ')', '[', ']', '{', '}', '\"', '|', '\\', '+', '-', ':', '#', '/', '!', '?', ',', '.']

# Words and phrases that would imply the file is a chapter
CHAP = ["chap.", "chtp", "ch", "chapter", "chap"]

# Takes a search term and returns path to resulting image
def get_image(search_term):
    response = google_images_download.googleimagesdownload()
    arguments = {"keywords":search_term,
                 "limit":1,
                 "aspect_ratio":"square",
                 "no_directory":True}
    paths = response.download(arguments)
    return paths[search_term][0]


class Library:
    base_dir = ""

    def __init__(self):
        pass

    def __init__(self, library_dir):
        if (os.is_dir(library_dir)):
            base_dir = library_dir
        else:
            raise NotADirectoryError(library_dir + ": not a valid directory")

    # This function moves the audiobook and cover to pre-specified library location
    # This should not be called until tags have been written, and a cover has
    # been found and downloaded
    def add_book(self, book):
        if (book is not Audiobook):
            raise TypeError("Illegal type: Expecting Audiobook")

        new_location = os.path.join(self.base_dir, book.author)

        # If directory doesn't exist, make one
        if (not os.is_dir(new_location)):
            self.add_author(book.author)

        new_location = os.path.join(new_location, book.title)

        # Make sure title directory exists
        if (not os.is_dir(new_location)):
            os.mkdir(new_location)

        # Get audio file extension
        file_extension = os.path.splitext(book.audio_location)[1]

        new_location = os.path.join(new_location, (book.title + file_extension))

        # Move audio file
        if (args.d):

        os.rename(book.audio_location, new_location)

        # Update location in class
        book.audio_location = new_location

        # Get image file extension
        file_extension = os.path.splitext(book.image_location)[1]

        # Set new location of image file
        new_location = os.path.join(self.base_dir,
                                    book.author,
                                    book.title,
                                    ("folder" + file_extension))

        # Move and rename file to "folder" with the original extension
        os.rename(book.image_location, new_location)

        # Update book image location
        book.image_location = new_location
    
    def add_author(self, author):
        new_location = os.path.join(self.base_dir, author)
        if (os.is_dir(new_location)):
            return
        else:
            os.mkdir(new_location)

            # Get author image
            image_location = get_image("\"" + author + "\" author")

            # Get file extension
            file_extension = os.path.splitext(image_location)[1]

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
    year = 0
    description = ""
    is_excerpt = False

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
        self.year = 0
        self.description = ""
        self.is_excerpt = False

    def __init__(self, location):
        self.title = ""
        self.subtitle = ""
        self.author = ""
        self.publisher = ""
        self.genre = ""
        self.year = 0
        self.description = ""
        self.audio_location = location
        self.is_excerpt = False

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

    # Write tags to audio file
    def write_tags(self):
        # Assume it's .ogg for now, add more functionality when this works properly
        try:
            audio_file = OggVorbis(self.audio_location)
        except MutagenError:
            print("Loading failed :(")

        audio_file["TITLE"] = self.title
        audio_file["ALBUM"] = self.title
        audio_file["ARTIST"] = self.author
        audio_file["PRODUCER"] = self.publisher
        audio_file["DATE"] = self.year
        audio_file["DESCRIPTION"] = self.description
        
        audio_file.save()

    # Get a cover image for the audiobook
    def get_cover(self):
        # Since I have yet to find an audiobook cover database,
        # we're using Google image search
        # https://github.com/hardikvasa/google-images-download
        response = google_images_download.googleimagesdownload()
        search_term = "\"" + self.author + " " + self.title + " audiobook\""
        arguments = {"keywords":search_term,
                     "limit":1,
                     "aspect_ratio":"square",
                     "no_directory":True}
        paths = response.download(arguments)

        # Keep hold of location and name for later
        self.image_location = paths[search_term][0]

    # Search Google Books API for information about book
    def get_info(self):
        # Get filename
        search_term = os.path.basename(self.audio_location)
        print("Getting info for: " + search_term)

        # Get rid of file extension
        print("Removing extension for: " + search_term)
        search_term = os.path.splitext(search_term)[0]

        # We will work with lowercase strings
        search_term = search_term.lower()

        # Set reminder if file is an excerpt
        if "excerpt" in search_term:
            print("File: \"" + search_term + "\" is an excerpt.")
            self.is_excerpt = True
            search_term.replace("excerpt", '')

        # Remove unhelpful words
        print("Removing unhelpful words.")
        for word in WORDS:
            search_term.replace(word, ' ')

        # Remove special characters
        print("Removing unhelpful characters.")
        for char in SPEC_CHARS:
            search_term.replace(char, '')

        # Handle chapters
        # We'll get back to this

        # Search Google Books API
        print("Sending Google Books API request.")
        response = requests.get("https://www.googleapis.com/books/v1/volumes?q=" +
                            search_term.replace(' ', '+'))

        # Make JSON response readable
        print("Loading response.")
        response = json.loads(response)

        # Compare titles by iterating through titles and seeing which ones match original
        # While Google Books search is good, occasionally it returns books that are 
        # clearly not a match, so we will crosscheck the result with the original string
        # and see which one is the closest
        # For now we will use the Levenshtein algorithm to compute similarity
        print("Finding closest match.")
        match
        ratio = 0.0
        for item in response["items"]:
            response_title = item["volumeInfo"]["title"]
            response_subtitle = item["volumeInfo"]["subtitle"]
            response_author = item["volumeInfo"]["authors"]["0"]
            # Try once without subtitle added to test string
            if (Levenshtein.ratio(response_title + " " +
                                  response_author, search_term) > ratio):
                match = item["volumeInfo"]
                ratio = Levenshtein.ratio(response_title + " " +
                                          response_author, search_term)
            # Try again WITH subtitle added to test string
            if (Levenshtein.ratio(response_title + " " +
                                  response_subtitle + " " +
                                  response_author, search_term) > ratio):
                match = item["volumeInfo"]
                ratio = Levenshtein.ratio(response_title + " " +
                                          response_subtitle + " " +
                                          response_author, search_term)

        # Write match info to Audiobook object
        print("Capturing book info.")
        self.title = match["title"]
        self.subtitle = match["subtitle"]
        self.author = match["authors"]["0"]
        self.publisher = match["publisher"]
        self.genre = match["categories"]["0"]
        self.year = re.match(r"(?<!\d)\d{4}(?!\d", match["publishedDate"])
        self.description = match["description"]

# Iterate through folder
for audio_file in os.listdir(args.directory):
    
    # Create library
    library = Library(AUDIOBOOK_DIR)

    # Create object that we will be working with
    book = Audiobook(os.path(audio_file))

    # Cleanse filename
    # For now, we are assuming all files are .ogg format and have no tags, so just use filenames
    search_term = audio_file

    # We will work with lowercase strings
    search_term.lower()

    # If file contains "excerpt", delete it

    # Remove unhelpful words
    for word in WORDS:
        search_term.replace(word, ' ')

    # Remove special characters
    for char in SPEC_CHARS:
        search_term.replace(char, '')

    # Handle chapters/parts
    # We'll get back to this

    # Search Google Books API
    response = requests.get("https://www.googleapis.com/books/v1/volumes?q=" +
                            search_term.replace(' ', '+'))

    # Make JSON response readable
    response = json.loads(response)

    # Compare titles by iterating through titles and seeing which ones match original
    # While Google Books search is good, occasionally it returns books that are 
    # clearly not a match, so we will crosscheck the result with the original string
    # and see which one is the closest
    # For now we will use the Levenshtein algorithm to compute similarity
    match
    ratio = 0.0
    for item in response["items"]:
        response_title = item["volumeInfo"]["title"]
        response_subtitle = item["volumeInfo"]["subtitle"]
        response_author = item["volumeInfo"]["authors"]["0"]
        if (Levenshtein.ratio(response_title + " " +
                              response_author, search_term) > ratio):
            match = item["volumeInfo"]
            ratio = Levenshtein.ratio(response_title + " " +
                                      response_author, search_term)
        if (Levenshtein.ratio(response_title + " " +
                              response_subtitle + " " +
                              response_author, search_term) > ratio):
            match = item["volumeInfo"]
            ratio = Levenshtein.ratio(response_title + " " +
                                      response_subtitle + " " +
                                      response_author, search_term)

    # Write match info to Audiobook object
    book.title = match["title"]
    book.subtitle = match["subtitle"]
    book.author = match["authors"]["0"]
    book.publisher = match["publisher"]
    book.genre = match["categories"]["0"]
    book.year = re.match(r"(?<!\d)\d{4}(?!\d", match["publishedDate"])
    book.description = match["description"]

    # Get cover image
    book.get_cover()

    # If '-d' file not given, make a copy of the original file
    shutil.copy2(book.audio_location, )

    # Add tags
    book.write_tags()

    # Move to audiobooks folder
    library.add_book(book)






