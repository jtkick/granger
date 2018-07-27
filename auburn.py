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
# For getting arguments
import argparse
# For comparing titles after Google Books API search
import Levenshtein
#import re
# For reading and writing audio tags
import mutagen

__author__ = "Jared Kick"
__copyright__ = ""
__credits__ = ["Jared Kick"]
__license__ = "GPL"
__version__ = "0.0.2"
__maintainer__ = "Jared Kick"
__email__ = "jaredkick@gmail.com"
__status__ = "Prototype"

parser = argparse.ArgumentParser(description="Import audiobooks in directory.")
parser.add_argument("directory")

# Flag to delete original audio file
parser.add_argument("-d", action="store_true")
args = parser.parse_args()

# This should be in a config file
AUDIOBOOK_DIR = "/home/jared/New_Audiobooks"

# Words to remove that tend to appear in file names but don't describe the book
# These words (especially "audiobook") tend to screw up Google Books searches
WORDS = ["audiobooks", "audiobook", "audio", "book", " by ", "narrated", "full", "complete", "hd", "pdf", "abridged", "unabridged", "subtitles", ".com", ".net", ".org", "mp3", "mp4", "m4v", "m4a", "m4b", "wav", "wmv"]

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

        # If directory doesn't exist, make one
        if (not os.path.isdir(new_location)):
            self.add_author(book.author)

        new_location = os.path.join(new_location, book.title)

        # Make sure title directory exists
        if (not os.path.isdir(new_location)):
            os.mkdir(new_location)

        # Get audio file extension
        file_extension = os.path.splitext(book.audio_location)[1]

        new_location = os.path.join(new_location, (book.title + file_extension))

        # Move audio file
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
        if (os.path.isdir(new_location)):
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
    year = ""
    description = ""

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

    # Write tags to audio file
    def write_tags(self):
        # Assume it's .ogg for now, add more functionality when this works properly
        #try:
        audio_file = mutagen.File(self.audio_location)
        #except MutagenError:
        #    print("Loading failed :(")

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
    
    # Search Google Books API for information about book and
    # write to Audiobook object
    def get_info(self):
        # Get filename
        search_term = os.path.basename(self.audio_location)
        print("Getting info for: " + search_term)

        # Get rid of file extension
        search_term = os.path.splitext(search_term)[0]

        # We will work with lowercase strings
        search_term = search_term.lower()

        # Set reminder if file is an excerpt
        if "excerpt" in search_term:
            print("File: \"" + search_term + "\" is an excerpt.")
            self.is_excerpt = True
            search_term.replace("excerpt", '')

        # Remove unhelpful words
        for word in WORDS:
            search_term.replace(word, ' ')

        # Remove special characters
        for char in SPEC_CHARS:
            search_term.replace(char, '')

        # Handle chapters
        # We'll get back to this
        # If chapter is found, it takes precedence over parts
        # i.e. 

        # Handle parts
        # Since some assholes like to format parts backwards, i.e. part one
        # of three is written 3/1, we will break it up and take the smallest
        PART_IDENTIFIERS = [" part", " pt"]

        # Search Google Books API
        print("Sending Google Books API request.")
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

        # TODO: FIND CUT-OFF LEVENSHTEIN RATIO

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
            self.year = match["publishedDate"]
            #book.year = re.match(r"(?<!\d)\d{4}(?!\d)", match["publishedDate"])
        if "description" in match:
            self.description = match["description"]

        # Keep an eye on what Google response is
        print("Google says:")
        print("Title:    " + book.title)
        print("Subtitle: " + book.subtitle)
        print("Author:   " + book.author)



# Subdirectories are ussumed to be separate books and will be treated as such
def main():
    library = Library(AUDIOBOOK_DIR)

    # Iterate through folder
    for audio_file in os.listdir(args.directory):

        # Create object that we will be working with
        print(AUDIOBOOK_DIR)
        book = Audiobook(os.path.join(args.directory, audio_file))

        # Cleanse filename
        # For now, we are assuming all files are .ogg format and have no tags, so just use  filenames
        search_term = os.path.splitext(audio_file)[0]

        # We will work with lowercase strings
        search_term = search_term.lower()

        # If file contains "excerpt", delete it

        # Remove unhelpful words
        print("Removing unhelpful words from filename...")
        for word in WORDS:
            search_term = search_term.replace(word, ' ')

        # Remove special characters
        print("Removing unhelpful characters from filename...")
        for char in SPEC_CHARS:
            search_term = search_term.replace(char, '')

        # Handle chapters/parts
        # We'll get back to this

        # Search Google Books API
        print("Searching Google API for: \"" + search_term + "\"...")
        response = requests.get("https://www.googleapis.com/books/v1/volumes?q=" +
                                search_term.replace(' ', '+'))

        # Make JSON response readable
        response = json.loads(response.text)


        # Compare titles by iterating through titles and seeing which ones match original
        # While Google Books search is good, occasionally it returns books that are 
        # clearly not a match, so we will crosscheck the result with the original string
        # and see which one is the closest
        # For now we will use the Levenshtein algorithm to compute similarity
        print("Comparing results to original title...")
        match = ""
        ratio = 0.0
        for item in response["items"]:
            response_title = ""
            response_subtitle = ""
            response_author = ""
            if "title" in item["volumeInfo"]:
                response_title = item["volumeInfo"]["title"]
            if "subtitle" in item["volumeInfo"]:
                response_subtitle = item["volumeInfo"]["subtitle"]
            if "authors" in item["volumeInfo"]:
                response_author = item["volumeInfo"]["authors"][0]
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

        

        # Get cover image
        print("Downloading book cover...")
        book.get_cover()

        # Add tags
        print("Writing audio file tags...")
        book.write_tags()

        # Move to audiobooks folder
        library.add_book(book)

if __name__ == "__main__":
    main()
