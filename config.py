#!/usr/bin/env python
# Auburn configuration file
# https://martin-thoma.com/configuration-files-in-python/

# Location of audiobook library
# This is where all new audiobooks given in the arguments will be stored
# Structure assumed to be: /path/to/library/author/book/book.ogg
AUDIOBOOK_DIR = ""

# Delete files after importing
# If 'True', Auburn will remove audio files from given directory
# when importing to library
DELETE = False