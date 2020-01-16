import config
import mutagen
import os
import shutil
import requests
import argparse
import sys
import re

import auburn

# This is what we are going to use to build our new audiobook file
class Audiobook:
    title = ""
    subtitle = ""
    author = ""
    publisher = ""
    genre = ""
    year = 0
    description = ""
    is_excerpt = False
    is_valid = False

    # Keep track of the current relative path of the audiobook file and
    # it's corresponding cover file
    directory = ""
    audio_location = ""
    image_location = ""

    def __init__(self):
        self.title = ""
        self.subtitle = ""
        self.author = ""
        self.publisher = ""
        self.genre = ""
        self.year = 0
        self.description = ""
        self.is_excerpt = False
        self.audio_location = ""
        self.image_location = ""

    def __init__(self, location):
        self.title = ""
        self.subtitle = ""
        self.author = ""
        self.publisher = ""
        self.genre = ""
        self.year = 0
        self.description = ""
        self.is_excerpt = False
        self.audio_location = location
        self.image_location = ""

    # Print audiobook, mostly for debugging and testing purposes
    def __str__(self):
        return ("Title:       " + self.title + "\n" +
                "Subtitle:    " + self.subtitle + "\n" +
                "Author:      " + self.author + "\n" +
                "Publisher:   " + self.publisher + "\n" +
                "Year:        " + self.year + "\n" +
                "Description: " + self.description + "\n" +
                "Audio Loc.:  " + self.audio_location + "\n" +
                "Image Loc.:  " + self.image_location)

    # Writes tags to audio file 'self'
    # Path to the audio file should be passed to the function
    def write_tags(self):
        # Assume it's .ogg for now, add more functionality when this works properly
        audio_file = mutagen.File(self.audio_location)

        audio_file["TITLE"] = self.title
        audio_file["ALBUM"] = self.title
        audio_file["ARTIST"] = self.author
        audio_file["PRODUCER"] = self.publisher
        audio_file["DATE"] = self.year
        audio_file["DESCRIPTION"] = self.description

        audio_file.save()

    # Simply returns match ratio
    # Used when sorting the list of matches received from Google Books
    def get_ratio(match):
        return match["ratio"]

    # Get a cover image for the audiobook
    def get_cover(self):
        self.image_location = auburn.get_image("\"" + self.author + " " + self.title + " audiobook\"")

    # Search Google Books API for information about book based on
    # file name and write to Audiobook object
    def get_info(self):
        # Get filename
        filename = os.path.basename(self.audio_location)

        # Split filename
        search_term, ext = os.path.splitext(filename)

        # Make sure file is valid
        if ext in config.FORMATS:
            self.is_valid = True
        else:
            if args.verbose:
                print("\"" + ext + "\" is not in valid format list. Skipping.")
            self.is_valid = False
            return

        # We will work with lowercase strings
        search_term = search_term.lower()

        # Set reminder if file is an excerpt
        if "excerpt" in search_term:
            if args.verbose:
                print("File: \"" + filename + "\" is an excerpt.")
            self.is_excerpt = True
            search_term = search_term.replace("excerpt", '')

        # Remove unhelpful words
        for word in config.WORDS:
            search_term = search_term.replace(word, ' ')

        # Remove special characters
        for char in config.SPEC_CHARS:
            search_term = search_term.replace(char, ' ')

        # TODO: HANDLE CHAPTERS
        # We'll get back to this
        # If chapter is found, it takes precedence over parts
        # i.e.

        # TODO: HANDLE PARTS
        # Since some assholes like to format parts backwards, i.e. part one
        # of three is written 3/1, we will break it up and take the smallest

        # This loop is to make sure the user confirms the info found
        info_correct = False
        while not info_correct:
            # Search Google Books API
            response = requests.get("https://www.googleapis.com/books/v1/volumes?q=" +
                                    search_term.replace(' ', '+'))

            # Make JSON response readable
            response = response.json()

            # Compare titles by iterating through titles and seeing which ones match original
            # While Google Books search is good, occasionally it returns books that are
            # clearly not a match, so we will crosscheck the result with the original string
            # and see which one is the closest
            matches = []
            if "items" in response:
                for item in response["items"]:
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
                    matches.append(match)

            # Sort list according to similarity ratio in descending order
            matches.sort(key=get_ratio(), reverse=true) 

            # Best match should be at the top of the list
            match = matches.pop(0)

            user_input = "NULL"
            while (user_input == "NULL"):
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
                print(colors.OKBLUE + "Filename: " + colors.WARNING + filename)
                if "title" in match["info"]:
                    print(colors.OKBLUE + "Title:    " + colors.OKGREEN + match["info"]["title"])
                if "subtitle" in match["info"]:
                    print(colors.OKBLUE + "Subtitle: " + colors.OKGREEN + match["info"]["subtitle"])
                if "authors" in match["info"]:
                    print(colors.OKBLUE + "Author:   " + colors.OKGREEN + match["info"]["authors"][0])
                else:
                    print(colors.OKBLUE + "Author:   " + colors.OKGREEN + "Unknown Author")

                # Prompt user if necessary
                user_input = "NULL"
                if not info_correct:
                    valid_options = ['A', 'a', 'M', 'm', 'E', 'e', 'S', 's', 'B', 'b', '']
                    while (user_input not in valid_options):
                        # Prompt user for input
                        print(colors.WARNING + "Is this information correct?")
                        print(colors.WARNING + "Options: [A]pply, [M]ore Candidates, [E]nter Search, [S]kip, A[B]ort")
                        user_input = input(colors.WARNING + "Command:" + colors.RESET + " ")

                    if user_input == 'A' or user_input == 'a':
                        # Exit loop and write match information
                        info_correct = True

                    elif user_input == 'M' or user_input == 'm':
                        print()
                        i = 1
                        for item in matches:
                            print(colors.WARNING + i +
                                  " - " + "{:.0%}".format(match["ratio"]) +
                                  " - " + item["info"]["title"] + " " + item["info"]["subtitle"] +
                                  " - " + item["info"]["authors"][0])
                            i += 1

                        selection = -1
                        while (selection <= 0 or selection > len(matches)):
                            input("\nEnter selection: ")
                            
                        # Swap matches
                        matches.append(match)
                        match = matches.pop(selection-1)
                        matches.sort(key=get_ratio(), reverse=true) 

                    elif user_input == 'E' or user_input == 'e':
                        # Do it again with new information
                        search_term = input("Title: ")
                        search_term += " " + input("Author: ")
                        search_term = search_term.lower()
                        user_input = "NULL"

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
            self.year = str(re.match(r"(?<!\d)\d{4}(?!\d)", match["info"]["publishedDate"]))
        if "description" in match["info"]:
            self.description = match["info"]["description"]
