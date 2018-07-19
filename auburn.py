#!/usr/bin/env python

# A simple script that takes audiobook files, renames them, and tags them properly

# For downloading audiobook cover art
from google_images_download import google_images_download
# For using the Google Book API
#from apiclient.discovery import build
import requests
# For manipulating API responses
import json
# For various system commands like moving and renaming files
import os
# For getting arguments
import argparse
# For comparing titles after Google Books API search
import Levenshtein
import re

__author__ = "Jared Kick"
__copyright__ = ""
__credits__ = ["Jared Kick"]
__license__ = "GPL"
__version__ = "0.0.1"
__maintainer__ = "Jared Kick"
__email__ = "jaredkick@gmail.com"
__status__ = "Prototype"

parser = argparse.ArgumentParser(description="Import audiobooks in directory.")
parser.add_argument('directories')

AUDIOBOOK_DIR = "/home/jared/Software/Development/Auburn/AUDIOBOOK_DIR/"

# Words to remove that tend to appear in file names but don't describe the book
# These words (especially "audiobook") tend to screw up Google Books searches
WORDS = ["audio", "book", " by ", "narrated", "full", "complete", "hd", "pdf", "abridged", "unabridged", "subtitles", ".com", ".net", ".org", "mp3", "mp4", "m4v", "m4a", "m4b"]

# Special characters to remove from filename. '&' and ''' are NOT removed as these are sometimes helpful
SPEC_CHARS = ['~', '`', '@', '$', '%', '^', '*', '_', '=', '<', '>', '(', ')', '[', ']', '{', '}', '\"', '|', '\\', '+', '-', ':', '#', '/', '!', '?', ',', '.']

# Words and phrases that would imply the file is a chapter
CHAP = ["chap.", "chtp", "ch", "chapter", "chap"]

# Path to directory with raw input files
raw_file_dir = sys.argv[1]

class Audiobook:
    """This is what we are going to use to build our new audiobook file"""
    
    title = ""
    subtitle = ""
    author = []
    publisher = ""
    genre = ""
    year = 0
    description = ""
    ratio = 0.0
    
    def __init__(self):
        self.title = ""
        self.subtitle = ""
        self.author = []
        self.publisher = ""
        self.genre = ""
        self.year = 0
        self.description = ""
        self.ratio = 0.0

    # Used to write tags to audio file
    def write_file(self, file):
        pass

# Iterate through folder
for audio_file in os.listdir(raw_file_dir):
    
    # Cleanse filename
    # For now, we are assuming all files are .ogg format and have no tags, so just use filenames

    search_term = audio_file

    # We will work exclusively with lowercase strings
    search_term.lower()

    # If file contains "excerpt", delete it

    # Remove unhelpful words
    for word in WORDS:
        search_term.replace(word, ' ')

    # Remove special characters
    for char in SPEC_CHARS:
        search_term.replace(char, '')

    # Make it fit API syntax
    #search_term.replace(' ', '+')

    # Handle chapters/parts
    # We'll get back to this

    # Search Google Books API
    # https://developers.google.com/api-client-library/python/start/get_started#building-and-calling-a-service
    # https://developers.google.com/books/docs/v1/getting_started
    # Build service
    #service = build('books', 'v1')
    # Setup API collection
    #collection = service.volume()
    # Make request
    #request = collection.list()
    # Send request
    #response = request.execute()
    # Print response (temporary)
    #print json.dumps(response, sort_keys=True, indent=4)
    response = requests.get("https://www.googleapis.com/books/v1/volumes?q=" + search_term.replace(' ', '+'))

    # Make JSON response readable
    response = json.loads(response)

    book = Audiobook()

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
        if (Levenshtein.ratio(response_title + " "
                            + response_author, search_term) > ratio):
            match = item["volumeInfo"]
            ratio = Levenshtein.ratio(response_title + " "
                                    + response_author, search_term)
        if (Levenshtein.ratio(response_title + " "
                            + response_subtitle + " "
                            + response_author, search_term) > ratio):
            match = item["volumeInfo"]
            ratio = Levenshtein.ratio(response_title + " "
                                    + response_subtitle + " "
                                    + response_author, search_term)

    book.title = match["title"]
    book.subtitle = match["subtitle"]
    book.author = match["authors"]["0"]
    book.publisher = match["publisher"]
    book.genre = match["categories"]["0"]
    book.year = re.match(r"(?<!\d)\d{4}(?!\d", match["publishedDate"])
    book.description = match["description"]

    # Rename filename

    # Add tags

    # Get audiobook cover art
    # Since I have yet to find an audiobook cover database,
    # we're using Google image search
    # https://github.com/hardikvasa/google-images-download
    response = google_images_download.googleimagesdownload()\
    search_term = "\"" + book.author + " " + book.title + " audiobook\""
    arguments = {"keywords":search_term, "limit":1, "aspect_ratio":"square", "no_directory":True}
    paths = response.download(arguments)

    # Keep hold of location and name for later
    image_location = paths[search_term][0]
    filename = os.path.basename(image_location)
    print(filename)

    # Get filename extension
    filename, file_extension = os.path.splitext(image_location)

    print(filename)
    print(file_extension)
    # Rename file to "folder" with the original extension
    os.rename(filename + file_extension, AUDIOBOOK_DIR + "folder" + file_extension)

    # Move to audiobooks folder