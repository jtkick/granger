class Library:
    base_dir = ""
    authors = []

    def __init__(self):
        pass

    def __init__(self, library_dir):
        if (os.path.isdir(library_dir)):
            self.base_dir = library_dir
        else:
            raise NotADirectoryError(library_dir + ": not a valid directory")

    # This function moves the audiobook and cover to pre-specified library location
    # This should not be called until tags have been written, and a cover has
    # been found and downloaded
    def add_book(self, book):
        # if (book is not Audiobook):
        #    raise TypeError("Illegal type: Expecting Audiobook")

        new_location = os.path.join(self.base_dir, book.author)

        # TODO: Add author the proper way, then add book to author
        # If directory doesn't exist, make one
        if not os.path.isdir(new_location):
            self.add_author(book.author)

        new_location = os.path.join(new_location, book.title)

        # Make sure title directory exists
        if not os.path.isdir(new_location):
            os.mkdir(new_location)

        # Get audio file extension
        file_extension = os.path.splitext(book.audio_location)[-1]

        new_location = os.path.join(new_location, (book.title + file_extension))

        # Move audio file
        if os.path.isfile(new_location):
            # If the book already exists in the library, do one of the following
            if config.OVERWRITE == "bitrate":
                old_file = mutagen.File(new_location)
                new_file = mutagen.File(book.audio_location)
                # If new file's bitrate is higher, remove the old file
                if new_file.info.bitrate > old_file.info.bitrate:
                    # Remove old file and add new file
                    os.remove(new_location)
                    shutil.copy2(book.audio_location, new_location)
            elif config.OVERWRITE == "size":
                # If new file is bigger, remove the old file
                if os.path.getsize(book.audio_location) > os.path.getsize(new_location):
                    # Remove old file and add new file
                    os.remove(new_location)
                    shutil.copy2(book.audio_location, new_location)
            elif config.OVERWRITE == "always":
                # Remove old file and add new file
                os.remove(new_location)
                shutil.copy2(book.audio_location, new_location)
            elif config.OVERWRITE != "never":
                print("Invalid value for \"OVERWRITE\" in configuration file.")
                raise ValueError
        else:
            # If theres nothing there, just copy it
            shutil.copy2(book.audio_location, new_location)

        # Delete audio file
        if config.DELETE or args.delete:
            os.remove(book.audio_location)

        # Update location in class regardless
        book.audio_location = new_location

        # Get image file extension
        file_extension = os.path.splitext(book.image_location)[1]

        # Set new location of image file
        new_location = os.path.join(self.base_dir,
                                    book.author,
                                    book.title,
                                    ("folder" + file_extension))

        # Move and rename file to "folder" with the original extension
        if os.path.isfile(new_location):
            os.remove(new_location)
        os.rename(book.image_location, new_location)

        # Update book image location
        book.image_location = new_location

    # Returns true if author is already in the library
    def has_author(self, name):
        for author in authors:
            if author.name == name:
                return True
        return False

    def add_author(self, author):
        new_location = os.path.join(self.base_dir, author)
        if (os.path.isdir(new_location)):
            return
        else:
            os.mkdir(new_location)

            # Get author image
            image_location = get_image("\"" + author + "\" author")

            # Get file extension
            file_extension = os.path.splitext(image_location)[-1]

            # All images are named 'folder'
            new_location = os.path.join(new_location, ("folder" + file_extension))

            # Move image to library author directory
            os.rename(image_location, new_location)

    def add_author(self, name):
