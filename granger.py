#!/usr/bin/env python3

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
import signal
import logging
import datetime
import string

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

# Setup command line arguments
parser = argparse.ArgumentParser(description="Import audiobooks in directory or file.")
parser.add_argument("input", nargs='*')
parser.add_argument("-d", "--delete", help="Delete original audio file after importing.", action="store_true")
parser.add_argument("-r", "--recursive", help="Recurse down through given directories.", action="store_true")
parser.add_argument("-v", "--verbose", help="Increase output verbosity.", action="store_true")
parser.add_argument("-u", "--dry-run", help="Do not move or edit files.", action="store_true")
parser.add_argument("-s", "--single-thread", help="Run in single thread mode.", action="store_true")
parser.add_argument("-j", "--write-json", help="Write metadata to JSON file.", action="store_true")
parser.add_argument("-i", "--no-images", help="Skip downloading cover images for book and author.", action="store_true")
parser.add_argument('-e', '--write-description', help='Write book summary to desc.txt file for Booksonic.', action='store_true')
parser.add_argument("-l", "--log-level", choices=["debug", "info", "warning", "error", "critical"], help="Set the log level to be stored in granger.log.", default="info")

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
    
def select_thread(name, library, dry_run):
    # Loop through audiobooks while previous thread (fetch) is not done
    while not fetch_done or not fetch_to_select_queue.empty():
        # Get audiobook from queue, blocking if queue is empty
        audiobook = fetch_to_select_queue.get(True, None)
        # Only select info if audiobook was received
        if audiobook:
            # Select correct info
            audiobook.select_info()
            # Handle pre-existing book
            if audiobook.add_to_library:
                library.check_existing(audiobook)
            # Push audiobook onto next queue, blocking if queue is full
            # Only add book if it is valid
            if audiobook.add_to_library and not dry_run:
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


def main():

    # Setup SIGTERM handling
    signal.signal(signal.SIGTERM, terminate)

    # Setup logger
    logging.basicConfig(filename='granger.log', format='[%(asctime)s] %(process)d: %(message)s', level=logging.INFO)
    if args.log_level == 'debug':
        logging.getLogger().setLevel(logging.DEBUG)
    elif args.log_level == 'info':
        logging.getLogger().setLevel(logging.INFO)
    elif args.log_level == 'warning':
        logging.getLogger().setLevel(logging.WARNING)
    elif args.log_level == 'error':
        logging.getLogger().setLevel(logging.ERROR)
    elif args.log_level == 'critical':
        logging.getLogger().setLevel(logging.CRITICAL)
    else:
        print('ERROR: Invalid log level')
        sys.exit(1)

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
                for (root, directories, files) in os.walk(file_or_dir, topdown=False):
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
            print('What have you brought on this cursed land?')
            sys.exit()
    
    # Group similar files into separate audiobooks
    if files_to_import:
        audiobooks = library.group_files(files_to_import)
    else:
        return

    if args.single_thread:

        logging.info('Running in single-thread mode')

        # Do everything one-by-one
        for i, audiobook in enumerate(audiobooks):

            # Fetch preliminary info
            logging.info('Fetching info for book %d of %d', i+1, len(audiobooks))
            audiobook.get_info()

            # Prompt user to select info
            logging.info('Prompting user for correct info')
            audiobook.select_info()

            # Check for existing book
            if audiobook.add_to_library:
                library.check_existing(audiobook)

            # Add book to library
            if audiobook.add_to_library:
                if not args.dry_run:
                    logging.info('Adding book %d of %d to library', i+1, len(audiobooks))
                    library.add_book(audiobook, config.DELETE or args.delete)
                else:
                    logging.info('Dry-run mode, not adding to library')
            else:
                logging.info('Book not valid, not adding to library')

    else:
        # Create threads
        logging.info('Starting worker threads')
        fetch_info_thread = threading.Thread(target=fetch_thread,
                                             args=("fetch_info_thread",
                                                   audiobooks))
        select_info_thread = threading.Thread(target=select_thread,
                                              args=("select_info_thread",
                                                    library,
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
        logging.info('Waiting for select_info thread to finish')
        select_info_thread.join()
    
        # If select_info thread exits (user aborts) close the fetch thread and
        # wait for write thread to finish
        if fetch_info_thread.is_alive():
            logging.info('fetch_info thread still alive, killing thread')
            stop_fetch_thread()
        logging.info('Waiting for fetch_info thread to finish')
        fetch_info_thread.join()

        stop_write_thread()

        # Wait for write thread to finish
        logging.info('Waiting for write_book thread to finish')
        write_book_thread.join()


#########################################################
#                       CLASSES                         #
#########################################################

class Library:
    base_dir = ""
    authors = []

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
                
                
    # Check if book exists in library and set data members accordingly
    def check_existing(self, audiobook):
        # Find author
        author = self.get_author(audiobook.author)
        
        # Check for existing book
        author.check_existing(audiobook)
                
                
    # Gets string and returns directory of author if they exist in library
    def get_author(self, author_name):
        # Cleanse input author name
        #clean_author_name = re.sub(r'[^a-z]+', '', author_name.lower())
        
        # Look for author of same name
        for author in self.authors:
            if author.name == author_name:
                logging.info('Found existing author of name: \'%s\'', author.name)
                return author
        
        # Otherwise create new author
        author = self.add_author(author_name)
        
        return author
                
                
    # Group similar files for import
    # Take a list of file names and create a list of Audiobook objects
    def group_files(self, filenames):
        # Create list of lists of similar filenames
        grouped_files = [[filenames[0]]]
        filenames.pop(0)
        for name in filenames:
            used = False
            for book in grouped_files:
                
                # Cleanse both names
                temp_name = name
                temp_book = book[0]

                # Use only lower case
                temp_name = temp_name.lower()
                temp_book = temp_book.lower()

                # Remove all non-alpha characters
                temp_name = re.sub(r"[^a-z]+", "", temp_name)
                temp_book = re.sub(r"[^a-z]+", "", temp_book)

                # Remove chapter and part identifiers
                identifiers = [ "part", "pt", "prt", "chap", "chapt", "chapter", "cpt", "chpt"]
                for word in identifiers:
                    temp_name = temp_name.replace(word, '')
                    temp_book = temp_book.replace(word, '')

                if temp_name == temp_book:
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

        for book in books:
            logging.info('Grouped files:')
            for audio_file in book.audio_files:
                logging.info('\t%s', os.path.basename(audio_file.file_abs_path))
            
        return books


    # This function moves the audiobook and cover to pre-specified library
    # location
    def add_book(self, book, delete):
        # Get cover image
        if not args.no_images:
            book.get_cover()

        # Get author
        author = self.get_author(book.author)
    
        # Add book to author
        author.add_book(book, delete)


    def add_author(self, name):
        # If author already exists, just return
        for author in self.authors:
            if name == author.name:
                return

        # Otherwise create new author
        author = Author(self.base_dir, name)

        # Create path for author
        if not os.path.isdir(author.directory):
            os.mkdir(author.directory)

            # Get author image
            if not args.no_images:
                author.get_cover()

        # Add newly created author to library object
        self.authors.append(author)
        
        return author
        
        
class Author:

    # Absolute path of the author
    # In most cases this will be the same as the author name
    directory = ""
    image_location = None
    # Name of the author
    name = ""
    # Should contain only 'audiobook' objects
    books = []

    def __init__(self, base_dir, author_name):
        self.name = author_name
        # TODO: SANITIZE NAME FOR DIRECTORY
        self.directory = os.path.join(base_dir, author_name)

    # Add book will update the 'books' list as well as move the audiobook and cover files to
    # the proper directory
    # This function should only be called by library.add_book()
    def add_book(self, book, delete):
        # Directory that book will be moved to
        book.directory = os.path.join(self.directory, book.title)

        # Make sure book directory exists
        if not os.path.isdir(book.directory):
            os.mkdir(book.directory)

        # Delete pre-existing book
        if book.delete_existing:
            # Get all files in directory
            files = [f for f in os.listdir(book.directory) if os.path.isfile(os.path.join(book.directory, f))]
            
            # Delete every file
            for f in files:
                os.remove(os.path.join(book.directory, f))
        
        # TODO: REWRITE METADATA FILES IF THEY ALREADY EXIST
        
        # Copy over new book
        for audio_file in book.audio_files:
            # Get file extension
            ext = os.path.splitext(audio_file.file_abs_path)[-1]
            
            # Create new audio file location
            new_location = os.path.join(book.directory, (audio_file.title + ext))
            
            # If same filename exists, we still want to keep both
            num = 1
            while os.path.isfile(new_location):
                filename, ext = os.path.splitext(new_location)
                new_location = filename + " " + str(num) + ext
                num += 1
            
            # If delete source file
            if delete:
                # Move instead of copying
                logging.info('Moving file: %s', os.path.basename(audio_file.file_abs_path))
                logging.info('Destination: %s', new_location)
                shutil.move(audio_file.file_abs_path, new_location)
                
            else:
                # Copy file
                logging.info('Copying file: %s', os.path.basename(audio_file.file_abs_path))
                logging.info('Destination: %s', new_location)
                shutil.copy2(audio_file.file_abs_path, new_location)
                
            # Update file path
            audio_file.file_abs_path = new_location
            
        # Update audiobook object to contain all existing files for writing metadata
        files = [f for f in os.listdir(book.directory) if os.path.isfile(os.path.join(book.directory, f))]
        for f in files:
            # Add_file returns if audiobook already contains file, so try all of them
            book.add_file(os.path.join(book.directory, f))

        # Get image file location
        if book.image_location:
            file_extension = os.path.splitext(book.image_location)[-1]

            # Set new location of image file
            new_location = os.path.join(book.directory, "cover" + file_extension)

            # Move and rename file to "cover"
            shutil.move(book.image_location, new_location)
            book.image_location = new_location

        # Write tags to audio file
        book.write_tags()
        
        # Update file stats
        book.get_stats()
        
        # Write json metadata file
        if args.write_json:
            book.write_json()

        # Write description file
        if args.write_description:
            book.write_description()

        # Add book to author
        self.books.append(book)
        
        
    def check_existing(self, book):
        # Get directory of author if they already exist in the library
        audiobook_dir = os.path.join(self.directory, book.title)
        
        if os.path.isdir(audiobook_dir):
          
            # Audiobook already exists in library
            files = [f for f in os.listdir(audiobook_dir) if os.path.isfile(os.path.join(audiobook_dir, f))]

            # Create audiobook object out of existing files
            existing_book = Audiobook()
            for f in files:
                existing_book.add_file(os.path.join(audiobook_dir, f))

            # Get stats
            existing_book.get_stats()
                    
            if config.OVERWRITE == "bitrate":
                if book.bitrate > existing_book.bitrate:
                    book.delete_existing = True
                          
            elif config.OVERWRITE == "size":
                if book.size > existing_book.size:
                    book.delete_existing = True
                            
            elif config.OVERWRITE == "always":
                book.delete_existing = True
                        
            elif config.OVERWRITE == "never":
                book.add_to_library = False
                       
            elif config.OVERWRITE == "prompt":
                # Prompt user
                print()
                print(colors.ENDC + 'Book already exists in library.')
                print(colors.OKGREEN + 'Existing book:')
                for audio_file in existing_book.audio_files:
                    print(colors.ENDC + '    ' + os.path.basename(audio_file.file_abs_path))
                print(colors.OKBLUE + '    Bitrate: ' + colors.ENDC + str(int(existing_book.bitrate/1000)) + ' Kb/s')
                print(colors.OKBLUE + '    Size:    ' + colors.ENDC + str(int(existing_book.size/1000000)) + ' MB')
                
                print(colors.OKBLUE + '    Length:  ' + colors.ENDC + format_length(existing_book.length))
                print()
                print(colors.OKGREEN + 'New book:')
                for audio_file in book.audio_files:
                    print(colors.ENDC + '    ' + audio_file.title + os.path.splitext(audio_file.file_abs_path)[-1])
                print(colors.OKBLUE + '    Bitrate: ' + colors.ENDC + str(int(book.bitrate/1000)) + ' Kb/s')
                print(colors.OKBLUE + '    Size:    ' + colors.ENDC + str(int(book.size/1000000)) + ' MB')
                print(colors.OKBLUE + '    Length:  ' + colors.ENDC + format_length(book.length))
                        
                user_input = None
                valid_options = ['A', 'a', 'K', 'k', 'M', 'm', 'B', 'b', '']
                while user_input not in valid_options:
                    print()
                    print(colors.WARNING + 'Options: [A]dd new book, [k]eep old book, [m]erge books, a[b]ort')
                    user_input = input(colors.WARNING + 'Command:' + colors.RESET + ' ')
                            
                if user_input in ['A', 'a', '']:
                    book.delete_existing = True
                            
                elif user_input in ['K', 'k']:
                    book.add_to_library = False
                            
                elif user_input in ['M', 'm']:
                    book.delete_existing = False
                    
                elif user_input == 'B' or user_input == 'b':
                    logging.info('User aborted program, exiting thread')
                    # Pull the plug
                    sys.exit()
                    
            else:
                logging.critical("Invalid value for \"OVERWRITE\" in configuration file.")
                raise ValueError


    def get_cover(self):
        # Get author image
        logging.info('Getting image for author: %s', self.name)
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

    # Metadata
    aggregate_rating = 0.0
    author = ""
    bitrate = 0 # In bits/second 
    content_rating = ""
    date_published = None
    description = ""
    duration = 0.0 # In seconds 
    genre = ""
    is_abridged = False
    is_excerpt = False
    isbn = "" # Prefer ISBN 13
    num_ratings = 0
    publisher = ""
    size = 0 # In bytes
    subtitle = ""
    title = ""

    # Holds list of matches from Google Books API
    matches = []

    # Location of where audiobook will be written
    directory = ""
    
    # Signifies that data in object is good and should be added
    add_to_library = False
    
    # Signifies that any existing audiobook files of the same name and author should be removed
    delete_existing = False
    
    # List of Audio_File objects
    audio_files = []
    
    # Location of the book cover image
    image_location = ""


    def __init__(self):
        self.aggregate_rating = 0.0
        self.author = ""
        self.bitrate = 0
        self.content_rating = ""
        self.date_published = None
        self.delete_existing = False
        self.description = ""
        self.duration = 0.0
        self.genre = ""
        self.is_abridged = False
        self.is_excerpt = False
        self.add_to_library = False
        self.isbn = ""
        self.num_ratings = 0
        self.publisher = ""
        self.size = 0
        self.subtitle = ""
        self.title = ""
        self.matches = []
        self.directory = ""
        self.audio_files = []
        self.image_location = ""


    # Print audiobook, mostly for debugging and testing purposes
    def __str__(self):
        return ("Title:       " + self.title + "\n" +
                "Subtitle:    " + self.subtitle + "\n" +
                "Author:      " + self.author + "\n" +
                "Year:        " + str(self.year) + "\n" +
                "Description: " + self.description)


    # Add audio file to audiobook object
    def add_file(self, filename):
        # Get file exension
        ext = os.path.splitext(filename)[-1]
        
        # Only add if it doesn't already exist
        for audio_file in self.audio_files:
            if filename == audio_file.file_abs_path:
                return
        
        # Only add acceptable file formats
        if ext in FORMATS:
            self.audio_files.append(Audio_File(filename))


    # Get a cover image for the audiobook
    def get_cover(self):
        logging.info('Getting image for book: %s', self.title)
        self.image_location = get_image("\"" + self.title + "\" audiobook")


    # Search Google Books API for information about book based on file name
    def get_info(self, search_term=None):

        # Get book stats
        self.get_stats()

        # Get rid of old matches
        self.matches = []

        # If search_term is not specified in parameters, get info from filename
        if search_term is None:

            # Gets similarity between all filenames in Audiobook to use as search term
            search_term = os.path.splitext(os.path.basename(self.audio_files[0].file_abs_path))[0]

            # Remove part and chapter numbers
            search_term = re.sub(self.audio_files[0].PART_FINDER_REGEX_STRING, '', search_term)

            # Use only lower-case letters for simplicity
            search_term = search_term.lower()

            # Find and remove website names
            website_domains = [ ".com", ".net", ".org", ".io", ".cc" ]
            for domain in website_domains:
                search_term = re.sub("[^a-z0-9][a-z0-9]*\\" + domain, "", search_term)

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

        logging.info('Fetching info for search term: %s', search_term)

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
                # Make sure there is a space after any punctuation in the title
                if 'title' in item['volumeInfo']:
                    item['volumeInfo']['title'] = re.sub(r'([\.,!?;:-])(?=[^ \.,!?;:\-$])', r'\1 ', item['volumeInfo']['title'])
            
                # If author is formatted like "J.R.R. Tolkien", replace with "J. R. R. Tolkien"
                if 'authors' in item['volumeInfo']:
                    item['volumeInfo']['authors'][0] = re.sub(r'(.\.)(?=[^ ])', r'\1 ', item['volumeInfo']['authors'][0])
            
                # If author is formatted like "J R R Tolkien", replace with "J. R. R. Tolkien"
                if 'authors' in item['volumeInfo']:
                    item['volumeInfo']['authors'][0] = re.sub(r'(?<=[^a-zA-Z])?([A-Z])([ ])', r'\1.\2', item['volumeInfo']['authors'][0])
                    
                # Fix capitalizations of title, subtitle, and author
                # Do NOT capitalize articles, coordinate conjunctions, nor prepositions
                # that are shorter than three letters long
                if 'title' in item['volumeInfo']:
                    item['volumeInfo']['title'] = titleify(item['volumeInfo']['title'])
                if 'subtitle' in item['volumeInfo']:
                    item['volumeInfo']['subtitle'] = titleify(item['volumeInfo']['subtitle'])
                if 'authors' in item['volumeInfo']:
                    item['volumeInfo']['authors'][0] = titleify(item['volumeInfo']['authors'][0])
            
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

            logging.info('Received %d matches for search term: %s', len(self.matches), search_term)

            # Sort list according to similarity ratio in descending order
            self.matches = sorted(self.matches, key = lambda i: i["ratio"], reverse=True)
            
            # Organize all files by parts
            if len(self.audio_files) > 1:
                self.get_parts()
            
            
    # Get stats (bitrate, length, and size)
    def get_stats(self):
    
        # Get size, average bitrate, and length
        total_size = 0
        average_bitrate = 0
        total_length = 0
        
        # Loop over all files in audiobook
        for audio_file in self.audio_files:
            # Update individual file stats
            audio_file.get_stats()
            
            # Calculate overall book stats
            total_size += audio_file.size
            average_bitrate += audio_file.size * audio_file.bitrate
            total_length += audio_file.length

        # Get weighted average
        if total_size:
            average_bitrate /= total_size
        
        self.size = total_size
        self.bitrate = average_bitrate
        self.length = total_length


    # Organize audio_files by high-level part, then chapter, then low-level part
    def get_parts(self):
        # Get parts and chapters
        for audio_file in self.audio_files:
            audio_file.get_parts()
        
        # Sort files in audiobook
        self.audio_files.sort()
        
        
    def select_info(self):
        info_correct = False
        
        # Get match candidate from top of sorted list
        match = None
        if len(self.matches) > 0:
            match = self.matches.pop(0)
        
        # Keep going until user or Granger decides match is good    
        print()
        while not info_correct:
            if match:
                # Successful search
                if match['ratio'] >= 0.5:
                    # Skip user prompt if prompt level is 'never' or 'medium'
                    if config.PROMPT_LEVEL == 0 or config.PROMPT_LEVEL == 1:
                        info_correct = True
                    # Notify user how close of a match it was
                    print(colors.ENDC + 'Similarity: ' + colors.OKGREEN + 'Good ' +
                          colors.BOLD + '(' + '{:.0%}'.format(match['ratio']) + ')' + colors.ENDC + ' ')
                # Not quite sure
                if match['ratio'] < 0.5 and match['ratio'] >= 0.25:
                    # Skip user prompt if prompt level is 'never'
                    if config.PROMPT_LEVEL == 0:
                        info_correct = True
                    # Notify user how close of a match it was
                    print(colors.ENDC + 'Similarity: ' + colors.WARNING + 'Moderate ' +
                          colors.BOLD + '(' + '{:.0%}'.format(match['ratio']) + ')' + colors.ENDC + ' ')
                # Bad match
                if match['ratio'] < 0.25:
                    # Skip user prompt if prompt level is 'never' and throw out file
                    if config.PROMPT_LEVEL == 0:
                        info_correct = True
                        self.add_to_library = False
                        return
                    # Notify user how close of a match it was
                    print(colors.ENDC + 'Similarity: ' + colors.FAIL + 'Bad ' +
                          colors.BOLD + '(' + '{:.0%}'.format(match['ratio']) + ')' + colors.ENDC + ' ')

                # Display what the program found
                if 'title' in match['info']:
                    print(colors.OKBLUE + 'Title:    ' + colors.ENDC + match['info']['title'])
                
                    # Set title in audio files for later
                    for audio_file in self.audio_files:
                        audio_file.set_title(match['info']['title'])

                    
                if 'subtitle' in match['info']:
                    print(colors.OKBLUE + 'Subtitle: ' + colors.ENDC + match['info']['subtitle'])
                if 'authors' in match['info']:
                    print(colors.OKBLUE + 'Author:   ' + colors.ENDC + match['info']['authors'][0])
                else:
                    print(colors.OKBLUE + 'Author:   ' + colors.ENDC + 'Unknown Author')
            # Otherwise, no matches have been found
            else:
                print(colors.FAIL + 'No matches found!' + colors.RESET + ' ')
                print(colors.OKBLUE + 'Title:')
                print(colors.OKBLUE + 'Author:')
            
            # Print filename renames
            print(colors.OKBLUE + 'Filenames: ')
            for audio_file in self.audio_files:
                print('    ' + colors.ENDC + str(audio_file))
            print()

            # Prompt user if necessary
            user_input = None
            if not info_correct:
                valid_options = ['A', 'a', 'M', 'm', 'E', 'e', 'N', 'n', 'S', 's', 'B', 'b', '']
                while user_input not in valid_options:
                    # Prompt user for input
                    print(colors.ENDC + "Is this information correct?")
                    print(colors.WARNING + "Options: [A]pply, [m]ore candidates, [e]nter search, e[n]ter metadata manually, [s]kip, a[b]ort")
                    user_input = input(colors.WARNING + "Command:" + colors.RESET + " ")

                if user_input == 'A' or user_input == 'a' or user_input == '':
                    # Exit loop and write match information
                    logging.info('Applying selected info')
                    self.add_to_library = True
                    info_correct = True

                elif user_input == 'M' or user_input == 'm':
                    print()
                    if len(self.matches) < 1:
                        print(colors.FAIL + "No more matches!" + colors.RESET + " \n")
                    else:
                        i = 1
                        for item in self.matches:
                            msg = colors.RESET + str(i) + " - "
                            if item["ratio"] >= 0.5:
                                msg += colors.OKGREEN + "{:.0%}".format(item["ratio"])
                            elif item["ratio"] >= 0.25:
                                msg += colors.WARNING + "{:.0%}".format(item["ratio"])
                            else:
                                msg += colors.FAIL + "{:.0%}".format(item["ratio"])
                            
                            if "title" in item["info"]:
                                msg += colors.RESET + " - " + item["info"]["title"]
                            if "subtitle" in item["info"]:
                                msg += colors.RESET + ": " + item["info"]["subtitle"]
                            if "authors" in item["info"]:
                                msg += colors.RESET + " - " + item["info"]["authors"][0]
                            print(msg)
                            i += 1

                        selection = -1
                        while (selection <= 0 or selection > len(self.matches)):
                            try:
                                selection = int(input(colors.WARNING + "\nEnter selection:" + colors.RESET + " "))
                            except:
                                selection = -1

                            if selection < 1 or selection > len(self.matches):
                                print(colors.FAIL + "Enter number between 1 and " + str(len(self.matches)) + ".")
                            
                        # Swap matches
                        self.matches.append(match)
                        match = self.matches.pop(selection-1)
                        self.matches = sorted(self.matches, key = lambda i: i["ratio"], reverse=True) 

                elif user_input == 'E' or user_input == 'e':
                    # Do it again with new information
                    logging.info('Waiting for user to enter search term')
                    print()
                    search_term = input(colors.WARNING + "Title:" + colors.RESET + " ")
                    search_term += " " + input(colors.WARNING + "Author:" + colors.RESET + " ")
                    print()

                    search_term = search_term.lower()
                    
                    logging.info('Trying again with search term: %s', search_term)

                    # Get new matches
                    self.get_info(search_term)
                    
                    # Update match
                    match = None
                    if len(self.matches) > 0:
                        match = self.matches.pop(0)
                        
                elif user_input == 'N' or user_input == 'n':
                    # Let user set metadata
                    logging.info('Waiting for user to enter metadata')
                    print()
                    self.title = input(colors.WARNING + 'Title:' + colors.ENDC + ' ')
                    self.subtitle = input(colors.WARNING + 'Subtitle:' + colors.ENDC + ' ')
                    self.author = input(colors.WARNING + 'Author:' + colors.ENDC + ' ')
                    self.publisher = input(colors.WARNING + 'Publisher:' + colors.ENDC + ' ')
                    self.genre = input(colors.WARNING + 'Genre:' + colors.ENDC + ' ')
                    date = input(colors.WARNING + 'Publish date:' + colors.ENDC + ' ')
                    year = month = day = 1
                    matches = re.match("(\d{4})(?:-)?(\d{1,2})?(?:-)?(\d{1,2})?", date, re.MULTILINE)
                    if matches:
                        if matches.group(1):
                            year = int(matches.group(1))
                        if matches.group(2):
                            month = int(matches.group(2))
                        if matches.group(3):
                            day = int(matches.group(3))
                    self.date_published = datetime.date(year, month, day)
                    self.description = input(colors.WARNING + 'Description:' + colors.ENDC + ' ')
                    self.isbn = input(colors.WARNING + 'ISBN:' + colors.ENDC + ' ')
                    print()
                    
                    self.add_to_library = True
                    info_correct = True
                    
                    # Set file titles to new title
                    for audio_file in self.audio_files:
                        audio_file.set_title(self.title)
                    
                    # Don't apply match info
                    return

                elif user_input == 'S' or user_input == 's':

                    logging.info('Skipping book')

                    # Drop this book and move on
                    self.add_to_library = False
                    return

                elif user_input == 'B' or user_input == 'b':

                    logging.info('User aborted program, exiting thread')

                    # Pull the plug
                    sys.exit()

        # Write match info to Audiobook object
        if match:
            if "title" in match["info"]:
                self.title = match["info"]["title"]
                logging.info('Writing info to audiobook object: %s', self.title)
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
                year = month = day = 1
                matches = re.match("(\d{4})(?:-)?(\d{1,2})?(?:-)?(\d{1,2})?", match["info"]["publishedDate"], re.MULTILINE)
                if matches:
                    if matches.group(1):
                        year = int(matches.group(1))
                    if matches.group(2):
                        month = int(matches.group(2))
                    if matches.group(3):
                        day = int(matches.group(3))
                    self.date_published = datetime.date(year, month, day)
            if "description" in match["info"]:
                self.description = match["info"]["description"]
            if "industryIdentifiers" in match["info"]:
                for isbn in match["info"]["industryIdentifiers"]:
                    if isbn["type"] == "ISBN_10" and not self.isbn:
                        self.isbn = isbn["identifier"]
                    elif isbn["type"] == "ISBN_13":
                        self.isbn = isbn["identifier"]
                    elif isbn["type"] != "ISBN_10" and isbn["type"] != "ISBN_13":
                        logging.warning("Unexpected ISBN version: %s", isbn["type"])
            if "maturityRating" in match["info"]:
                self.content_rating = match["info"]["maturityRating"]
            if "averageRating" in match["info"]:
                self.aggregate_rating = match["info"]["averageRating"]

        else:
            self.title = ""
            self.subtitle = ""
            self.author = "Unknown Author"
            self.publisher = ""
            self.genre = ""
            self.date_published = ""
            self.description = ""
            self.isbn = ""
            self.content_rating = ""
            self.aggregate_rating = 0.0
            
        # Set title in audio files for later
        for audio_file in self.audio_files:
            audio_file.set_title(self.title)


    # Write description to it's own file, for use in Booksonic
    def write_description(self):
    
        # Write to file
        with open(os.path.join(self.directory, 'desc.txt'), 'w') as f:
            f.write(self.description)


    # Write metadata to JSON file
    def write_json(self):
       
        alternate_name = None
        if self.subtitle:
            alternate_name = self.title + ": " + self.subtitle
        
        date = str(self.date_published)
        if str(self.date_published) == '0001-01-01':
            date = None

        data = {
            'name': self.title,
            'alternateName': alternate_name,
            'author': {
                'name': self.author 
            },
            'description': self.description,
            'abridged': self.is_abridged,
            'isbn': self.isbn,
            'contentRating': self.content_rating,
            'aggregateRating': str(self.aggregate_rating),
            'datePublished': date,
            'genre': self.genre,
            'publisher': {
                'name': self.publisher
            },
            'bitrate': str(self.bitrate),
            'contentSize': str(self.size),
            'duration': str(self.length)
        }

        # Serialize json
        json_object = json.dumps(data, indent = 4)

        # Write to file
        with open(os.path.join(self.directory, self.title + '.json'), 'w') as f:
            f.write(json_object)


    # Writes tags to audio file 'self'
    # Path to the audio file should be passed to the function
    def write_tags(self):
        # Write each part of file individually
        for track, audio_file in enumerate(self.audio_files, 1):

            #try:
            if True:
                # Get file extension
                ext = os.path.splitext(audio_file.file_abs_path)[-1]
        
                # Open audio file
                audio = mutagen.File(audio_file.file_abs_path)
        
                # TODO: CLEAR ALL TAGS BEFORE WRITING
        
                # TODO: GET .WAV FILES WORKING
        
                logging.info('Attempting to open file for writing metadata: %s', audio_file.file_abs_path)

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
                    if self.date_published and self.date_published.year:
                        if self.date_published.year != '0001':
                            audio["date"] = str(self.date_published.year)
                        else:
                            audio["date"] = ""
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
                    if self.date_published and self.date_published.year:
                        if self.date_published.year != '0001':
                            audio["date"] = str(self.date_published.year)
                        else:
                            audio["date"] = ""
                    if self.description:
                        audio["description"] = self.description
                    if self.genre:
                        audio["genre"] = self.genre

                    audio["tracknumber"] = str(track)
                
                # Save changes to file
                audio.save()

            #except:
            else:
                logging.critical('Could not write metadata to file. Either corrupt or not an audio file.')

        
# This is the class that contains a file that is part of an Audiobook
class Audio_File:
    file_abs_path = ""
    title = ""
    size = 0
    bitrate = 0
    length = 0.0
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
        self.title = os.path.splitext(os.path.basename(self.file_abs_path))[0]
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
        
        
    # Get file stats
    def get_stats(self):
        self.size = os.path.getsize(self.file_abs_path)

        # Get file extension
        ext = os.path.splitext(self.file_abs_path)[-1]
        
        # Open audio file
        audio = None        
        logging.info('Attempting to open file for reading info: %s', os.path.basename(self.file_abs_path))

        # Handle different filetypes separately
        if ext in [".mp3"]:
            # Open audio file
            try:
                audio = EasyID3(self.file_abs_path)
            except:
                audio = mutagen.File(self.file_abs_path, easy=True)
                audio.add_tags()
                
        elif ext in [".mp4", ".m4a"]:
            # Open audio file
            audio = MP4(self.file_abs_path)

        else:
            audio = mutagen.File(self.file_abs_path)
                
        try:
            self.bitrate = audio.info.bitrate
        except:
            self.bitrate = 0
            
        try:
            self.length = audio.info.length
        except:
            self.length = 0

        # Save changes to file
        audio.save()


    # Uses the file_abs_path to get parts and chapters for organizing
    def get_parts(self):
        # Remove extension
        filename = os.path.splitext(os.path.basename(self.file_abs_path))[0]
        
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


#########################################################
#                   HELPER FUNCTIONS                    #
#########################################################

def reset_download_dir():
    download_dir = "/tmp/granger/"
    
    logging.info('Clearing download directory: %s', download_dir)

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
            logging.error('Failed to delete %s. Reason: %s', file_path, e)
        

# Takes a search term and returns path to resulting image
# google_images_download is not currently working
# Works with fork by Joeclinton1
# https://github.com/Joeclinton1/google-images-download/tree/patch-1
def get_image(search_term):
    # Cleanse search term
    search_term = search_term.replace(',', '')
    
    # Get single square image and store in /tmp
    response = google_images_download.googleimagesdownload()

    # Set download parameters
    arguments = {'keywords':search_term,
                 'limit':1,
                 'aspect_ratio':'square',
                 'output_directory':'/tmp/granger/',
                 'silent_mode':True}
    
    # Download images while redirecting output
    paths = response.download(arguments)

    try:
        return paths[0][search_term][0]
    except:
        logging.warning('No images downloaded for search term: %s', search_term)
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
    
# Takes length in seconds and returns formatted string
def format_length(length):
    length_str = ''
    hours = length / 3600
    minutes = (length % 3600) / 60
    seconds = length % 60
    if hours:
        length_str += str(int(hours)) + 'H'
    if minutes:
        length_str += ' ' + str(int(minutes)) + 'M'
    if seconds:
        length_str += ' ' + str(int(seconds)) + 'S'
    return length_str


# Close program gracefully on SIGTERM
def terminate(signal, frame):
    logging.info('Received SIGTERM signal, exiting.')
    print(colors.RESET + "Received SIGTERM signal, exiting...")
    stop_fetch_thread()
    stop_select_thread()
    stop_write_thread()
    
# Fix capitalizations of title and subtitle
# Do NOT capitalize articles, coordinate conjunctions, nor prepositions
# that are shorter than three letters long
def titleify(title):
    # Find and match Roman numerals
    matches = re.findall(r'(?:[^a-z0-9]|\s)?[IVXLDCM]{2,}(?:[^a-z0-9]|\s|$)', title, re.MULTILINE)
    
    title = title.lower()
    
    # Re-capitalize Roman numerals before splitting
    for match in matches:
        title = title.replace(match.lower(), match)
        
    for char in ['[', ']', '{', '}', '(', ')', '<', '>']:
        title = title.replace(char, '')

    words = title.split(' ')   
    title = string.capwords(words.pop(0))
    for word in words:
        if word in ['a', 'an', 'the', 'for', 'and', 'nor', 'but', 'or', 'yet', 'so',
                    'as', 'at', 'by', 'in', 'of', 'on', 'out', 'per', 'to', 'up', 'via']:
            title += ' ' + word
        else:
            if word.isupper():
                title += ' ' + word
            else:
                title += ' ' + string.capwords(word)
    
    # Find ': ' or ' - ' in string and capitalize next letter
    for match in re.findall(r'(?::| - )[^a-z]*[a-z]', title, re.MULTILINE):
        title = title.replace(match.lower(), string.capwords(match))
    
    return title


if __name__ == "__main__":
    main()
