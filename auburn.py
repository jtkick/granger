#!/usr/bin/env python

# A simple script that takes audiobook files, renames them, and tags them properly

# For downloading audiobook cover art
from google_images_download import google_images_download
# For using the Google Book API
from apiclient.discovery import build
# For manipulating API responses
import json
# For various system commands like moving and renaming files
import os

__author__ = "Jared Kick"
__copyright__ = ""
__credits__ = ["Jared Kick"]
__license__ = "GPL"
__version__ = "0.0.1"
__maintainer__ = "Jared Kick"
__email__ = "jaredkick@gmail.com"
__status__ = "Prototype"


AUDIOBOOK_DIR = "/home/jared/Software/Development/Auburn/AUDIOBOOK_DIR/"

# Iterate through folder

# Cleanse filename
# For now, we are assuming all files are .ogg format and have no tags, so just use filenames

    # If file contains "excerpt", delete it

    # Remove major words

    # Remove special characters

    # Handle chapters/parts

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

# Compare titles

# Rename filename

# Add tags


# Temporary inputs for testing
author = input("Enter author: ")
title = input("Enter title: ")

# Get audiobook cover art
# https://github.com/hardikvasa/google-images-download
response = google_images_download.googleimagesdownload()
# Set search keywords to "author book title - audiobook" and limit to one result
search_term = "\"" + author + " " + title + " audiobook\""

# Set Google search arguments
arguments = {"keywords":search_term, "limit":1, "aspect_ratio":"square", "no_directory":True}
# Download album art
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