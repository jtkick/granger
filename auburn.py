#!/usr/bin/env python

# A simple script that takes audiobook files, renames them, and tags them properly

# Config file
import config as config

# For downloading audiobook cover art
from google_images_download import google_images_download
from apiclient.discovery import build
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
import threading
import queue

import Audiobook
import Author
import Library


import re

__author__ = "Jared Kick"
__copyright__ = "Copyright 2018, Jared Kick, All rights reserved."
__credits__ = ["Jared Kick"]
__license__ = "GPL"
__version__ = "0.0.4"
__maintainer__ = "Jared Kick"
__email__ = "jaredkick@gmail.com"
__status__ = "Prototype"

# API info for image search
API_KEY = "AIzaSyC7fN6ZiyuIZaDCUI263B59cd4x_J4rDLQ"
CSE_ID = "008564407890452954709:flri5kdvz5k"

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

# Queues for passing Audiobook objects between threads
fetch_to_select_queue = queue.Queue()
select_to_write_queue = queue.Queue()

# Signals to tell threads when to stop processing
fetch_done = False
select_done = False

# Flag to manually stop 'fetch' thread abruptly
fetch_stop_flag = False

# Thread that fetches book info before being presented to the user
def fetch_thread(name, audiobooks):
    # Loop through given audiobooks
    for audiobook in audiobooks:
        # Check flag to see if thread should stop
        global fetch_stop_flag
        if fetch_stop_flag:
            sys.exit()
        # Get preliminary info for each
        audiobook.get_info()
        # Put on queue; block if queue is full
        fetch_to_select_queue.put(audiobook, True, None)
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

def main():

    # TODO: CHECK CONFIG AND ARGUMENTS
    
    # TODO: HANDLE DIFFERENT TYPES OF METADATA E.G., SCHEMA.ORG, BOOKSONIC, .NFO

    library = Library.Library(config.AUDIOBOOK_DIR)

    # This is the list of directories that we will look through
    # If recursive flag is there, we will add directories to this list
    directory = args.input
    
    # Get all files to import
    files_to_import = []
    if config.RECURSE or args.recursive:
        # Grab all files recursively
        for (root, directories, files) in os.walk(args.input, topdown=False):
            for name in files:
                # Make sure extension is valid
                ext = os.path.splitext(name)[-1]
                if ext in config.FORMATS:
                    files_to_import.append(os.path.join(root, name))
    # Otherwise, list all files in current directory
    else:
        for name in os.listdir(args.input):
            if os.path.isfile(name):
                # Make sure extension is valid
                ext = os.path.splitext(name)[-1]
                if ext in config.FORMATS:
                    files_to_import.append(os.path.join(directory, name))
    
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
    
    # Wait for threads to finish
    select_info_thread.join()
    # Make sure write thread is stopping
    stop_write_thread()
    # If select_info thread exits (user aborts) close the fetch thread and
    # wait for write thread to finish
    if fetch_info_thread.is_alive():
        fetch_stop_flag = True

    if write_book_thread.is_alive():
        print("Copying files. Do not exit...")
    write_book_thread.join()


if __name__ == "__main__":
    main()
