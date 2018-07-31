#!/usr/bin/env python
# Auburn configuration file
# https://martin-thoma.com/configuration-files-in-python/

# Location of audiobook library
# This is where all new audiobooks given in the arguments will be stored
# Structure assumed to be: /path/to/library/author/book/book.ogg
AUDIOBOOK_DIR = ""

# Delete files after importing
# If 'True', Auburn will remove audio files after importing to library
DELETE = False

# Overwrite pre-existing audiobook
# If a book that is being imported already exists in the library,
# overwrite the old one. Options are 'always', 'never', 'size', and 'bitrate'.
# 'always': Always overwrite pre-existing file
# 'never': Always keep pre-existing file
# 'size': Overwrite old file if new one is bigger
# 'bitrate': Overwrite old file if new one has a higher bitrate
OVERWRITE = "bitrate"