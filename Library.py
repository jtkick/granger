#!/usr/bin/env python

import os

import auburn
import Audiobook
import Author

class Library:
    base_dir = ""
    authors = {}

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
                
    # Group similar files for import
    # Take a list of file names and create a list of Audiobook objects
    def group_files(self, filenames):
        # Create list of lists of similar filenames
        grouped_files = [[filenames[0]]]
        filenames.pop(0)
        for name in filenames:
            used = False
            for book in grouped_files:
                if auburn.jaccard_similarity(name, book[0]) > 0.9:
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
            audiobook = Audiobook.Audiobook()
            for name in book:
                audiobook.add_file(name)
            books.append(audiobook)
            
        return books


    # This function moves the audiobook and cover to pre-specified library
    # location
    def add_book(self, book, delete):
        # Get cover image
        book.get_cover()

        # Write tags to audio file
        book.write_tags()

        # Create author if it doesn't exist
        self.add_author(book.author)
    
        # Add book to author
        self.authors[book.author].add_book(book, delete)


    def add_author(self, name):
        # If author already exists, just return
        if name in self.authors:
            return

        # Otherwise create new author
        author = Author.Author(self.base_dir, name)

        # Create path for author
        if not os.path.isdir(author.directory):
            os.mkdir(author.directory)

            # Get author image
            author.get_cover()

        # Add newly created author to library object
        self.authors[name] = author
