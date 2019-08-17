#!/usr/bin/env python
# Auburn configuration file
# https://martin-thoma.com/configuration-files-in-python/

# Location of audiobook library
# This is where all new audiobooks given in the arguments will be stored
# Structure assumed to be: /path/to/library/author/book/book.ogg
# Ex: AUDIOBOOK_DIR = "/path/to/library/"
AUDIOBOOK_DIR = "/home/jared/Audiobooks/"

# Delete files after importing
# If 'True', Auburn will remove original audio files after importing to library
# This can also be done on a case-by-case basis with the '-d' flag through the
# command line.
DELETE = True

# Recurse down through directories
# If 'True', Auburn will add all files in directory to the library including
# all files in subdirectories
RECURSE = True

# Prompt level
# If a book is not a good match, this determines whether the user is prompted to make a decision
# 0: The user is never prompted, and the book is imported or not, depending on the program's decision
# 1: The user is prompted when the program is not sure about a match
# 2: The user is always prompted, no matter how confident the program is in it's match
PROMPT_LEVEL = 2

# Overwrite pre-existing audiobook
# If a book that is being imported already exists in the library,
# overwrite the old one. Options are 'always', 'never', 'size', and 'bitrate'.
# 'always': Always overwrite pre-existing file
# 'never': Always keep pre-existing file
# 'size': Overwrite old file if new one is bigger
# 'bitrate': Overwrite old file if new one has a higher bitrate
OVERWRITE = "bitrate"

# Acceptable file extensions
# This is a list of the files that are considered acceptable audio files
# that will be processed as audiobooks. Any extension not in this list will
# be ignored when importing. Bear in mind there is no guarantee that mutagen
# will be able to handle any audio formats other than what is listed.
FORMATS = [".ogg", ".flac", ".mp3", ".mp4"]
