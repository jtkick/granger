#!/usr/bin/env python

# A simple script that takes audiobook files, renames them, and tags them properly

# For downloading audiobook cover art
from google_images_download import google_images_download
# For using the Google Book API
from apiclient.discovery import build
# For manipulating API responses
import json

__author__ = "Jared Kick"
__copyright__ = ""
__credits__ = ["Jared Kick"]
__license__ = "GPL"
__version__ = "0.0.1"
__maintainer__ = "Jared Kick"
__email__ = "jaredkick@gmail.com"
__status__ = "Prototype"

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
service = build('books', 'v1')
# Setup API collection
collection = service.volume()
# Make request
request = collection.list()
# Send request
response = request.execute()
# Print response (temporary)
print json.dumps(response, sort_keys=True, indent=4)

# Compare titles

# Rename filename

# Add tags

# Get audiobook cover art
# https://github.com/hardikvasa/google-images-download
response = google_images_download.googleimagesdownload()
# Set search keywords to "author book title - audiobook" and limit to one result
arguments = {"keywords": author + " \"" + title + "\"" + " - audiobook", "limit":1, "aspect_ratio":"square"}

paths = response.download(arguments)
print(paths)

# Move to audiobooks folder