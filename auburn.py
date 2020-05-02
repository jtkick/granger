#!/usr/bin/env python

# Config file
import config as config

from google_images_download import google_images_download
import requests
import json
import os
import shutil
import argparse
import sys
import threading
import queue
import mutagen
from mutagen.easyid3 import EasyID3
from mutagen.mp4 import MP4, MP4Cover
import re

__author__ = "Jared Kick"
__copyright__ = "Copyright 2018, Jared Kick, All rights reserved."
__credits__ = ["Jared Kick"]
__license__ = "GPL"
__version__ = "0.0.5"
__maintainer__ = "Jared Kick"
__email__ = "jaredkick@gmail.com"
__status__ = "Prototype"


FORMATS = [".ogg", ".flac", ".mp3", ".opus", ".m4a", ".mp4"]

# TODO: ADD DATABASE FUNCTIONALITY?

parser = argparse.ArgumentParser(description="Import audiobooks in directory or file.")
parser.add_argument("input", nargs='*')

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

# Queues for passing Audiobook objects between threads
fetch_to_select_queue = queue.Queue()
select_to_write_queue = queue.Queue()

# Signals to tell threads when to stop processing
fetch_done = False
select_done = False

# Flag to manually stop 'fetch' thread abruptly
fetch_stop_flag = False

def stop_fetch_thread():
    # Flag to manually stop 'fetch' thread abruptly
    global fetch_stop_flag
    fetch_stop_flag = True

# Thread that fetches book info before being presented to the user
def fetch_thread(name, audiobooks):
    # Loop through given audiobooks
    for audiobook in audiobooks:
        # Check flag to see if thread should stop
        global fetch_stop_flag
        if fetch_stop_flag:
            break
        # Get preliminary info for each
        audiobook.get_info()
        # Put on queue; block if queue is full
        fetch_to_select_queue.put(audiobook, True, None)
    stop_select_thread()

def stop_select_thread():
    # Tell select thread that all audiobooks are processed and in the queue
    # Send None message in queue to break out of .get() function
    fetch_to_select_queue.put(None, True, None)
    fetch_done = True
    
def select_thread(name, dry_run):
    # Loop through audiobooks while previous thread (fetch) is not done
    while not fetch_done or not fetch_to_select_queue.empty():
        # Get audiobook from queue, blocking if queue is empty
        audiobook = fetch_to_select_queue.get(True, None)
        # Only select info if audiobook was received
        if audiobook:
            # Select correct info
            audiobook.select_info()
            # Push audiobook onto next queue, blocking if queue is full
            # Only add book if it is valid
            if audiobook.is_valid and not dry_run:
                select_to_write_queue.put(audiobook, True, None)
        # If 'None' message received, that means there're no more audiobooks
        else:
            break
    stop_write_thread()
        
def stop_write_thread():
    # Tell write thread that all audiobooks are processed and in the queue
    # Send None message in queue to break out of .get() function
    select_to_write_queue.put(None, True, None)
    select_done = True
        
def write_thread(name, library, delete):
    # Prep downlaod directory
    reset_download_dir()
    
    # Loop through audiobooks while previous thread (select) is not done
    while not select_done or not select_to_write_queue.empty():
        # Get audiobook from queue, blocking if queue is empty
        audiobook = select_to_write_queue.get(True, None)
        if audiobook:
            # Write book to directory
            library.add_book(audiobook, delete)
        # If 'None' message received, that means there're no more audiobooks
        else:
            break
            
    # Clean downlaod directory
    reset_download_dir()


def reset_download_dir():
    download_dir = "/tmp/auburn/"
    
    # Ensure directory exists
    if not os.path.isdir(download_dir):
        os.mkdir(download_dir)
        
    # Empty directory
    for filename in os.listdir(download_dir):
        file_path = os.path.join(download_dir, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e))
        

# Takes a search term and returns path to resulting image
# google_images_download is not currently working
# Works with fork by Joeclinton1
# https://github.com/Joeclinton1/google-images-download/tree/patch-1
def get_image(search_term):
    # Cleanse search term
    search_term = search_term.replace(',', '')
    
    # Get single square image and store in /tmp
    response = google_images_download.googleimagesdownload()
    arguments = {"keywords":search_term,
                 "limit":1,
                 "aspect_ratio":"square",
                 "output_directory":"/tmp/auburn/",
                 "silent_mode":True}
    paths = response.download(arguments)

    try:
        return paths[0][search_term][0]
    except:
        return None


# Used to find similarity between filename and results from Google Books API
def jaccard_similarity(list1, list2):
    s1 = set(list1)
    s2 = set(list2)
    return len(s1.intersection(s2)) / len(s1.union(s2))
    
    
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


def main():

    # TODO: CHECK CONFIG AND ARGUMENTS
    
    # TODO: HANDLE DIFFERENT TYPES OF METADATA E.G., SCHEMA.ORG, BOOKSONIC, .NFO

    library = Library(config.AUDIOBOOK_DIR)

    # This is the list of directories that we will look through
    # If recursive flag is there, we will add directories to this list
    directory = args.input
    
    # Get all files to import
    files_to_import = []
    for file_or_dir in args.input:
        if os.path.isfile(file_or_dir):
            files_to_import.append(file_or_dir)
        elif os.path.isdir(file_or_dir):
            if config.RECURSE or args.recursive:
                # Grab all files recursively
                for (root, directories, files) in os.walk(args.input, topdown=False):
                    for name in files:
                        # Make sure extension is valid
                        ext = os.path.splitext(name)[-1]
                        if ext in FORMATS:
                            files_to_import.append(os.path.join(root, name))
            # Otherwise, list all files in current directory
            else:
                for name in os.listdir(args.input):
                    if os.path.isfile(name):
                        # Make sure extension is valid
                        ext = os.path.splitext(name)[-1]
                        if ext in FORMATS:
                            files_to_import.append(os.path.join(directory, name))
        else:
            print("What have you brought on this cursed land?")
            sys.exit()
    
    # Group similar files into separate audiobooks
    if files_to_import:
        audiobooks = library.group_files(files_to_import)
    else:
        return

    # Create threads
    fetch_info_thread = threading.Thread(target=fetch_thread,
                                         args=("fetch_info_thread",
                                               audiobooks))
    select_info_thread = threading.Thread(target=select_thread,
                                          args=("select_info_thread",
                                                args.dry_run))
    write_book_thread = threading.Thread(target=write_thread,
                                         args=("write_book_thread",
                                               library,
                                               config.DELETE or args.delete))
                                     
    # Start the threads
    fetch_info_thread.start()
    select_info_thread.start()
    write_book_thread.start()
    
    # Wait for user to finish selecting data, or to abort
    select_info_thread.join()
    
    # If select_info thread exits (user aborts) close the fetch thread and
    # wait for write thread to finish
    if fetch_info_thread.is_alive():
        stop_fetch_thread()
    
    # Make sure write thread is stopping
    stop_write_thread()

    # Let user know that data is still being processed
    if write_book_thread.is_alive():
        print("Copying files. Do not exit...")
        
    # Wait for write thread to finish
    write_book_thread.join()


class Library:
    base_dir = ""
    authors = {}

    def __init__(self, library_dir):
        if (os.path.isdir(library_dir)):
            self.base_dir = library_dir
        else:
            # If directory does not exist, try and create it
            try:
                os.mkdir(library_dir)
            except OSError:
                raise NotADirectoryError(library_dir + ": not a valid directory")
            else:
                self.base_dir = library_dir
                
    # Group similar files for import
    # Take a list of file names and create a list of Audiobook objects
    def group_files(self, filenames):
        # Create list of lists of similar filenames
        grouped_files = [[filenames[0]]]
        filenames.pop(0)
        for name in filenames:
            used = False
            for book in grouped_files:
                if jaccard_similarity(name, book[0]) > 0.9:
                    # Add part name to book
                    book.append(name)
                    used = True
                    break
            # If filename doesn't match any other books, create a new one
            if not used:
                grouped_files.append([name])
                
        # Group similar filenames into Audiobook
        books = []
        for book in grouped_files:
            audiobook = Audiobook()
            for name in book:
                audiobook.add_file(name)
            books.append(audiobook)
            
        return books


    # This function moves the audiobook and cover to pre-specified library
    # location
    def add_book(self, book, delete):
        # Get cover image
        book.get_cover()

        # Write tags to audio file
        book.write_tags()

        # Create author if it doesn't exist
        self.add_author(book.author)
    
        # Add book to author
        self.authors[book.author].add_book(book, delete)


    def add_author(self, name):
        # If author already exists, just return
        if name in self.authors:
            return

        # Otherwise create new author
        author = Author(self.base_dir, name)

        # Create path for author
        if not os.path.isdir(author.directory):
            os.mkdir(author.directory)

            # Get author image
            author.get_cover()

        # Add newly created author to library object
        self.authors[name] = author
        
        
class Author:

    # Absolute path of the author
    # In most cases this will be the same as the author name
    directory = ""
    image_location = None
    # Name of the author
    name = ""
    # Should contain only 'audiobook' objects in chronological order
    books = []

    def __init__(self, base_dir, author_name):
        self.name = author_name
        # TODO: SANITIZE NAME FOR DIRECTORY
        self.directory = os.path.join(base_dir, author_name)

    # Add book will update the 'books' list as well as move the audiobook and cover files to
    # the proper directory
    # This function should only be called by library.add_book() which will do the thinking
    # and is called in the main function.
    def add_book(self, book, delete):
        # TODO: FIX THE AWFUL LOGIC IN THIS FUNCTION
    
        book.directory = os.path.join(self.directory, book.title)

        # Make sure book directory exists
        if not os.path.isdir(book.directory):
            os.mkdir(book.directory)

        # Move/copy/delete audio files
        for audio_file in book.audio_files:
            # Get original file extension
            ext = os.path.splitext(audio_file.file_abs_path)[-1]
            
            # Define where the file will go and be named
            new_location = os.path.join(book.directory, (audio_file.title + ext))
            
            # Means we will add new book to library
            add = False
            # Move audio file
            if os.path.isfile(new_location):
                # If the book already exists in the library, do one of the following
                if config.OVERWRITE == "bitrate":
                    old_file = mutagen.File(new_location)
                    new_file = mutagen.File(audio_file.file_abs_path)
                    # If new file's bitrate is higher, remove the old file
                    if new_file.info.bitrate > old_file.info.bitrate:
                        # Remove old file and add new file
                        add = True

                elif config.OVERWRITE == "size":
                    # If new file is bigger, remove the old file
                    if os.path.getsize(audio_file.file_abs_path) > os.path.getsize(new_location):
                        # Remove old file and add new file
                        add = True
                elif config.OVERWRITE == "always":
                    # Remove old file and add new file
                    add = True
                elif config.OVERWRITE != "never":
                    print("Invalid value for \"OVERWRITE\" in configuration file.")
                    raise ValueError
            # File doesn't already exist, so add it
            else:
                add = True
            
            if delete and add:
                # Move file
                shutil.move(audio_file.file_abs_path, new_location)
                
                # Update file path
                audio_file.file_abs_path = new_location
                
            elif not delete and add:
                # Copy file
                shutil.copy2(audio_file.file_abs_path, new_location)
                
                # Update file path
                audio_file.file_abs_path = new_location
                
            else:
                return

        # Get image file location
        if book.image_location:
            file_extension = os.path.splitext(book.image_location)[-1]

            # Set new location of image file
            new_location = os.path.join(book.directory, "cover" + file_extension)

            # Move and rename file to "folder"
            shutil.move(book.image_location, new_location)
            book.image_location = new_location

        # Add book to author
        self.books.append(book)

        # Sort books by year
        self.books.sort(key=lambda x: x.year, reverse=True)

    def get_cover(self):
        # Get author image
        image_location = get_image("\"" + self.name + "\" author")

        if image_location:
            # Get file extension
            file_extension = os.path.splitext(image_location)[-1]

            # All author images are named "folder"
            self.image_location = os.path.join(self.directory, "folder" + file_extension)

            # Move image to library author directory
            shutil.move(image_location, self.image_location)
        

# This is what we are going to use to build our new audiobook file
class Audiobook:
    title = ""
    subtitle = ""
    author = ""
    publisher = ""
    genre = ""
    year = None
    description = ""
    genre = ""
    is_excerpt = False
    is_valid = False
    # Holds list of matches from Google Books API
    matches = []
    # List of Audio_File objects
    audio_files = []
    
    # Location of the book cover image
    image_location = ""

    def __init__(self):
        self.title = ""
        self.subtitle = ""
        self.author = ""
        self.publisher = ""
        self.genre = ""
        self.year = None
        self.description = ""
        self.genre = ""
        self.is_excerpt = False
        self.is_valid = False
        self.matches = []
        self.audio_files = []
        self.image_location = ""


    # Print audiobook, mostly for debugging and testing purposes
    def __str__(self):
        return ("Title:       " + self.title + "\n" +
                "Subtitle:    " + self.subtitle + "\n" +
                "Author:      " + self.author + "\n" +
                "Publisher:   " + self.publisher + "\n" +
                "Year:        " + str(self.year) + "\n" +
                "Description: " + self.description + "\n" +
                "Image Loc.:  " + self.image_location)

    # Add audio file to audiobook object
    def add_file(self, filename):
        self.audio_files.append(Audio_File(filename))

    # Writes tags to audio file 'self'
    # Path to the audio file should be passed to the function
    def write_tags(self):
        # Write each part of file individually
        for track, audio_file in enumerate(self.audio_files, 1):
            # Get file extension
            ext = os.path.splitext(audio_file.file_abs_path)[-1]
        
            # Open audio file
            audio = mutagen.File(audio_file.file_abs_path)
        
            # TODO: CLEAR ALL TAGS BEFORE WRITING
        
            # TODO: GET .WAV FILES WORKING
        
            # Handle different filetypes separately
            if ext in [".mp3"]:
                # Open audio file
                try:
                    audio = EasyID3(audio_file.file_abs_path)
                except:
                    audio = mutagen.File(audio_file.file_abs_path, easy=True)
                    audio.add_tags()
                
                # Write tags
                if audio_file.title:
                    audio["title"] = audio_file.title
                if self.title:
                    audio["album"] = self.title
                if self.author:
                    audio["artist"] = self.author
                if self.year:
                    audio["date"] = self.year
                if self.genre:
                    audio["genre"] = self.genre
                
                audio["tracknumber"] = str(track)
                
            elif ext in [".mp4", ".m4a"]:
                # Open audio file
                audio = MP4(audio_file.file_abs_path)
                
                # Write tags
                if audio_file.title:
                    audio["\xa9nam"] = audio_file.title
                if self.author:
                    audio["\xa9ART"] = self.author
                if self.title:
                    audio["\xa9alb"] = self.title
                
            # Handle file types separately
            else:
                # Write tags
                if audio_file.title:
                    audio["title"] = audio_file.title
                if self.title:
                    audio["album"] = self.title
                if self.author:
                    audio["artist"] = self.author
                if self.publisher:
                    audio["producer"] = self.publisher
                if self.year:
                    audio["date"] = self.year
                if self.description:
                    audio["description"] = self.description
                if self.genre:
                    audio["genre"] = self.genre

                audio["tracknumber"] = str(track)
                
            # Save changes to file
            audio.save()


    # Get a cover image for the audiobook
    def get_cover(self):
        self.image_location = get_image("\"" + self.title + "\" audiobook")


    # Search Google Books API for information about book based on file name
    def get_info(self, search_term=None):
        # If search_term is not specified in parameters, get info from filename
        if search_term is None:
            # Gets similarity between all filenames in Audiobook to use as search term
            search_term = os.path.splitext(os.path.basename(self.audio_files[0].file_abs_path))[0]

            search_term = search_term.lower()

            # Set reminder if file is an excerpt
            if "excerpt" in search_term:
                self.is_excerpt = True
                search_term = search_term.replace("excerpt", '')

            # Remove unhelpful words
            for word in config.WORDS:
                search_term = search_term.replace(word, ' ')

            # Remove special characters
            for char in config.SPEC_CHARS:
                search_term = search_term.replace(char, ' ')
                
        # Search Google Books API
        response = requests.get("https://www.googleapis.com/books/v1/volumes?q=" +
                                search_term.replace(' ', '+'))

        # Make JSON response readable
        response = response.json()

        # Compare titles by iterating through titles and seeing which ones match original
        # While Google Books search is good, occasionally it returns books that are
        # clearly not a match, so we will crosscheck the result with the original string
        # and see which one is the closest
        if "items" in response:
            for item in response["items"]:
                # Start by comparing with just the title
                response_str = ""
                if "title" in item["volumeInfo"]:
                    response_str += item["volumeInfo"]["title"]
                response_str = response_str.lower()
                # Remove special characters
                for char in config.SPEC_CHARS:
                    response_str = response_str.replace(char, ' ')
                ratio = jaccard_similarity(search_term.split(), response_str.split())
                match = {"ratio": ratio, "info": item["volumeInfo"]}
                
                # Search using just the title and author
                response_str = ""
                if "title" in item["volumeInfo"]:
                    response_str += item["volumeInfo"]["title"]
                if "authors" in item["volumeInfo"]:
                    response_str += " "
                    response_str += item["volumeInfo"]["authors"][0]
                response_str = response_str.lower()
                # Remove special characters
                for char in config.SPEC_CHARS:
                    response_str = response_str.replace(char, ' ')
                ratio = jaccard_similarity(search_term.split(), response_str.split())
                if ratio > match["ratio"]:
                    match = {"ratio": ratio, "info": item["volumeInfo"]}

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
                for char in config.SPEC_CHARS:
                    response_str = response_str.replace(char, ' ')
                ratio = jaccard_similarity(search_term.split(), response_str.split())
                if ratio > match["ratio"]:
                    match = {"ratio": ratio, "info": item["volumeInfo"]}

                # Add best match of this run to list of matches
                self.matches.append(match)

            # Sort list according to similarity ratio in descending order
            self.matches = sorted(self.matches, key = lambda i: i["ratio"], reverse=True)
            
            # Organize all files by parts
            self.organize_files()
            
    def select_info(self):
        info_correct = False
        
        # Get match candidate from top of sorted list
        match = self.matches.pop(0)
        
        # Keep going until user or Auburn decides match is good    
        while not info_correct:
            # Successful search
            if match["ratio"] >= 0.5:
                # Skip user prompt if prompt level is 'never' or 'medium'
                if config.PROMPT_LEVEL == 0 or config.PROMPT_LEVEL == 1:
                    info_correct = True
                # Notify user how close of a match it was
                print(colors.OKGREEN + "Similarity: Good " +
                      colors.BOLD + "(" + "{:.0%}".format(match["ratio"]) + ")" + colors.ENDC + " ")
            # Not quite sure
            if match["ratio"] < 0.5 and match["ratio"] >= 0.25:
                # Skip user prompt if prompt level is 'never'
                if config.PROMPT_LEVEL == 0:
                    info_correct = True
                # Notify user how close of a match it was
                print(colors.WARNING + "Similarity: Moderate " +
                      colors.BOLD + "(" + "{:.0%}".format(match["ratio"]) + ")" + colors.ENDC + " ")
            # Bad match
            if match["ratio"] < 0.25:
                # Skip user prompt if prompt level is 'never' and throw out file
                if config.PROMPT_LEVEL == 0:
                    info_correct = True
                    self.is_valid = False
                    return
                # Notify user how close of a match it was
                print(colors.FAIL + "Similarity: Bad " +
                      colors.BOLD + "(" + "{:.0%}".format(match["ratio"]) + ")" + colors.ENDC + " ")

            # Display what the program found
            if "title" in match["info"]:
                print(colors.OKBLUE + "Title:    " + colors.OKGREEN + match["info"]["title"])
                
                # Set title in audio files for later
                for audio_file in self.audio_files:
                    audio_file.set_title(match["info"]["title"])
                    
            if "subtitle" in match["info"]:
                print(colors.OKBLUE + "Subtitle: " + colors.OKGREEN + match["info"]["subtitle"])
            if "authors" in match["info"]:
                print(colors.OKBLUE + "Author:   " + colors.OKGREEN + match["info"]["authors"][0])
            else:
                print(colors.OKBLUE + "Author:   " + colors.OKGREEN + "Unknown Author")
            print(colors.OKBLUE + "Filenames: ")
            for audio_file in self.audio_files:
                print("\t" + colors.OKGREEN + str(audio_file))
            print()

            # Prompt user if necessary
            user_input = None
            if not info_correct:
                valid_options = ['A', 'a', 'M', 'm', 'E', 'e', 'S', 's', 'B', 'b', '']
                while user_input not in valid_options:
                    # Prompt user for input
                    print(colors.WARNING + "Is this information correct?")
                    print(colors.WARNING + "Options: [A]pply, [M]ore Candidates, [E]nter Search, [S]kip, A[B]ort")
                    user_input = input(colors.WARNING + "Command:" + colors.RESET + " ")

                if user_input == 'A' or user_input == 'a':
                    # Exit loop and write match information
                    self.is_valid = True
                    info_correct = True

                elif user_input == 'M' or user_input == 'm':
                    print()
                    i = 1
                    for item in self.matches:
                        msg = colors.WARNING + str(i) + " - {:.0%}".format(item["ratio"])
                        if "title" in item["info"]:
                            msg += " - " + item["info"]["title"]
                        if "subtitle" in item["info"]:
                            msg += ": " + item["info"]["subtitle"]
                        if "authors" in item["info"]:
                            msg += " - " + item["info"]["authors"][0]
                        print(msg)
                        i += 1

                    selection = -1
                    while (selection <= 0 or selection > len(self.matches)):
                        selection = int(input("\nEnter selection: "))
                            
                    # Swap matches
                    self.matches.append(match)
                    match = self.matches.pop(selection-1)
                    self.matches = sorted(self.matches, key = lambda i: i["ratio"], reverse=True) 

                elif user_input == 'E' or user_input == 'e':
                    # Do it again with new information
                    search_term = input("Title: ")
                    search_term += " " + input("Author: ")
                    search_term = search_term.lower()
                    # Get new matches
                    self.get_info(search_term)
                    # Update match
                    match = self.matches.pop(0)

                elif user_input == 'S' or user_input == 's':
                    # Drop this file and move on
                    self.is_valid = False
                    return

                elif user_input == 'B' or user_input == 'b':
                    # Pull the plug
                    sys.exit()

        # Write match info to Audiobook object
        if "title" in match["info"]:
            self.title = match["info"]["title"]
        if "subtitle" in match["info"]:
            self.subtitle = match["info"]["subtitle"]
        if "authors" in match["info"]:
            self.author = match["info"]["authors"][0]
        else:
            self.author = "Unknown Author"
        if "publisher" in match["info"]:
            self.publisher = match["info"]["publisher"]
        if "categories" in match["info"]:
            self.genre = match["info"]["categories"][0]
        if "publishedDate" in match["info"]:
            # Find four digit number
            matches = re.finditer(r"(?<!\d)\d{4}(?!\d)", match["info"]["publishedDate"])
            for date_match in matches:
                if date_match.group(0):
                    self.year = date_match.group(0)
        if "description" in match["info"]:
            self.description = match["info"]["description"]
        if "categories" in match["info"]:
            self.genre = match["info"]["categories"][0]
            
    
    # Organize audio_files by high-level part, then chapter, then low-level part
    def organize_files(self):
        # Get parts and chapters
        for audio_file in self.audio_files:
            audio_file.get_parts()
        
        # Sort files in audiobook
        self.audio_files.sort()

        
# This is the class that contains a file that is part of an Audiobook
class Audio_File:
    file_abs_path = ""
    title = ""
    # List of all high-level parts contained in this audio file
    high_parts = []
    # List of all chapters contained in this audio file
    chapters = []
    # List of all low-level parts contained in this audio file
    low_parts = []
    
    PART_FINDER_REGEX_STRING = "(?:[Pp][AaRrTtSs]{0,7}[^a-zA-Z0-9]{0,5}(\d+)(?:[^0-9-thr\v]{0,5}(\d+)|\s+[\Dthru-]{0,5}\s+(\d+))?|[^a-zA-z]+(\d+)[^0-9-thr\v]{1,5}(\d+)|\s+[Cc][HhAaPpTtEeRrSs]{0,8}[^a-zA-Z0-9]*(\d+)(?:[^0-9]{0,5}(\d+))?(?:\s+[Pp][AaRrTtSs]{0,6}[^a-zA-Z0-9]{0,5}(\d+)(?:[\D\-through\v]{0,5}(\d+)\s)?)?|(\d)\s*(?:\(.*\))?\s*$)"

    def __init__(self):
        self.file_abs_path = ""
        self.high_parts = []
        self.chapters = []
        self.low_parts = []

    def __init__(self, location):
        self.file_abs_path = location
        self.high_parts = []
        self.chapters = []
        self.low_parts = []
            
    def __str__(self):
        # Display current filename, and planned filename
        return (os.path.basename(self.file_abs_path) +
                " -> " +
                self.title +
                os.path.splitext(self.file_abs_path)[-1])
    
    # '<' operator for sorting        
    def __lt__(self, other):
        if self.high_parts < other.high_parts:
            return True
        elif self.chapters < other.chapters:
            return True
        elif self.low_parts < other.low_parts:
            return True
        else:
            return False
            
    # Sets the new filename from part and chapter numbers
    def set_title(self, book_title):
        # Start with book title
        self.title = book_title
        # Write part number
        if self.high_parts:
            if len(self.high_parts) == 1:
                self.title += " - Part " + self.high_parts[0]
            elif len(high_parts) > 1:
                self.title += " - Parts " + self.high_parts[0] + "-" + self.high_parts[-1]
        # Write chapter number
        if self.chapters:
            if len(self.chapters) == 1:
                self.title += " - Chapter " + self.chapters[0]
            elif len(high_parts) > 1:
                self.title += " - Chapters " + self.chapters[0] + "-" + self.chapters[-1]
        # Write low part number
        if self.low_parts:
            if len(self.low_parts) == 1:
                self.title += " - Part " + self.low_parts[0]
            elif len(self.low_parts) > 1:
                self.title += " - Parts " + self.low_parts[0] + "-" + self.low_parts[-1]
        
        
    # Uses the file_abs_path to get parts and chapters for organizing
    def get_parts(self):
        # Remove extension
        filename = os.path.splitext(self.file_abs_path)[0]
        
        # Parse file_abs_path for matches
        matches = re.finditer(self.PART_FINDER_REGEX_STRING, filename, re.MULTILINE)
    
        # Initialize variables
        high_part_num = 0
        num_high_parts = 0
        end_high_part_num = 0
        chapter_num = 0
        end_chapter_num = 0
        low_part_num = 0
        num_low_parts = 0
        # Get values from regex matches
        for match in matches:
            # Group 10: Higher part number
            if match.group(10) is not None:
                high_part_num = match.group(10)
            # Group 4: Higher part number
            if match.group(4) is not None:
                high_part_num = match.group(4)
            # Group 1: Higher part number
            if match.group(1) is not None:
                high_part_num = match.group(1)
            # Group 5: Number of higher parts
            if match.group(5) is not None:
                num_high_parts = match.group(5)
            # Group 2: Number of higher parts
            if match.group(2) is not None:
                num_high_parts = match.group(2)
            # Group 3: End of higher part range
            if match.group(3) is not None:
                end_high_part_num = match.group(3)
            # Group 6: Chapter number
            if match.group(6) is not None:
                chapter_num = match.group(6)
            # Group 7: End of chapter range
            if match.group(7) is not None:
                end_chapter_num = match.group(7)
            # Group 8: Lower part number
            if match.group(8) is not None:
                low_part_num = match.group(8)
            # Group 9: Number of lower parts
            if match.group(9) is not None:
                num_low_parts = match.group(9)

        # Make sure part numbers are in correct order
        if high_part_num and num_high_parts:
            if high_part_num > num_high_parts:
                high_part_num, num_high_parts = num_high_parts, high_part_num
        if low_part_num and num_low_parts:
            if low_part_num > num_low_parts:
                low_part_num, num_low_parts = num_low_parts, low_part_num

        # Write numbers to member variables
        if high_part_num and end_high_part_num:
            # Make sure numbers are in correct order
            if high_part_num > end_high_part_num:
                # Swap variables
                high_part_num, end_high_part_num = end_high_part_num, high_part_num
            self.high_parts = list(range(high_part, end_high_part_num + 1))
        elif high_part_num:
            self.high_parts = [ high_part_num ]
            
        if chapter_num and end_chapter_num:
            # Make sure numbers are in correct order
            if chapter_num > end_chapter_num:
                # Swap variables
                chapter_num, end_chapter_num = end_chapter_num, chapter_num
            self.chapters = list(range(chapter_num, end_chapter_num + 1))
        elif chapter_num:
            self.chapters = [ chapter_num ]
            
        if low_part_num:
            self.low_parts = [ low_part_num ]

if __name__ == "__main__":
    main()
