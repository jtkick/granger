import config
import mutagen
from mutagen.easyid3 import EasyID3
import os
import shutil
import requests
import argparse
import sys
import re
from difflib import SequenceMatcher

import auburn
import Audio_File

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
        self.audio_files.append(Audio_File.Audio_File(filename))

    # Writes tags to audio file 'self'
    # Path to the audio file should be passed to the function
    def write_tags(self):
        # Write each part of file individually
        for track, audio_file in enumerate(self.audio_files, 1):
            # Open file for writing
            tag = mutagen.File(audio_file.file_abs_path)

            # Write tags
            if audio_file.title:
                tag["TITLE"] = audio_file.title
            if self.title:
                tag["ALBUM"] = self.title
            if self.author:
                tag["ARTIST"] = self.author
            if self.publisher:
                tag["PRODUCER"] = self.publisher
            if self.year:
                tag["DATE"] = self.year
            if self.description:
                tag["DESCRIPTION"] = self.description
            if self.genre:
                tag["GENRE"] = self.genre
            tag["TRACKNUMBER"] = str(track)
        
            # Save changes to file
            tag.save()


    # Get a cover image for the audiobook
    def get_cover(self):
        self.image_location = auburn.get_image("\"" + self.title + "\" audiobook")


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
                ratio = auburn.jaccard_similarity(search_term.split(), response_str.split())
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
                ratio = auburn.jaccard_similarity(search_term.split(), response_str.split())
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
                ratio = auburn.jaccard_similarity(search_term.split(), response_str.split())
                if ratio > match["ratio"]:
                    match = {"ratio": ratio, "info": item["volumeInfo"]}

                # Add best match of this run to list of matches
                self.matches.append(match)

            # Sort list according to similarity ratio in descending order
            self.matches = sorted(self.matches, key = lambda i: i["ratio"], reverse=True)
            #self.matches.sort(key=get_ratio(), reverse=true)
            
            # Update part info
            for audio_file in self.audio_files:
                audio_file.get_parts()
            
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
    def organize_files():
        # Get parts and chapters
        for audio_file in self.audio_files:
            audio_file.get_parts()
        
        # Sort files in audiobook
        self.audio_files.sort()
