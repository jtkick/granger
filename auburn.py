#!/usr/bin/env python

# A simple script that takes audiobook files, renames them, and tags them properly

# For downloading audiobook cover art
from google_images_download import google_images_download


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

    # If file contains "excerpt", delete it

    # Remove major words

    # Remove special characters

    # Handle chapters/parts
    
# Search Google Books API

# Compare titles

# Rename filename

# Add tags

# Get audiobook cover art
# https://github.com/hardikvasa/google-images-download
response = google_images_download.googleimagesdownload()

arguments = {"keywords": "\"" + title + "\"" + author + " - audiobook", "limit":1, "aspect_ratio":"square"}

paths = response.download(arguments)
print(paths)

# Move to audiobooks folder