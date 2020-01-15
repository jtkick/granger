import config as config

class Author:

    # Absolute path of the author
    # In most cases this will be the same as the author name
    directory = ""
    image_location = ""
    # Name of the author
    name = ""
    # Should contain only 'audiobook' objects in chronological order
    books = []

    def __init__(self, base_dir, author_name):
        self.name = author_name
        # TODO: SANITIZE NAME FOR DIRECTORY
        self.directory = os.path.join(base_dir, author_name)

    # Add book will update the 'books' list as well as move the audiobook and cover files to
    # the proper directory
    # This function should only be called by library.add_book() which will do the thinking
    # and is called in the main function.
    def add_book(self, book):
        new_location = os.path.join(new_location, book.title)
        book.directory = new_location

        # Make sure title directory exists
        if not os.path.isdir(new_location):
            os.mkdir(new_location)

        # Get audio file extension
        file_extension = os.path.splitext(book.audio_location)[-1]

        new_location = os.path.join(new_location, (book.title + file_extension))

        # Means we will add new book to library
        add = False
        # Move audio file
        if os.path.isfile(new_location):
            # If the book already exists in the library, do one of the following
            if config.OVERWRITE == "bitrate":
                old_file = mutagen.File(new_location)
                new_file = mutagen.File(book.audio_location)
                # If new file's bitrate is higher, remove the old file
                if new_file.info.bitrate > old_file.info.bitrate:
                    # Remove old file and add new file
                    add = True

            elif config.OVERWRITE == "size":
                # If new file is bigger, remove the old file
                if os.path.getsize(book.audio_location) > os.path.getsize(new_location):
                    # Remove old file and add new file
                    add = True
            elif config.OVERWRITE == "always":
                # Remove old file and add new file
                add = True
            elif config.OVERWRITE != "never":
                print("Invalid value for \"OVERWRITE\" in configuration file.")
                raise ValueError

        # Delete and/or move file
        if ((config.DELETE or args.delete) and add):
            # Move file
            os.rename(book.audio_location, new_location)
        elif ((config.DELETE or args.delete) and not add):
            # Remove file
            os.remove(book.audio_location)
        elif (not(config.DELETE or args.delete) and add):
            # Copy file
            shutil.copy2(book.audio_location, new_location)
        else:
            return

        # Update location in class regardless
        book.audio_location = new_location

        # Get image file location
        file_extension = os.path.splitext(book.image_location)[1]

        # Set new location of image file
        new_location = os.path.join(book.directory, "folder" + file_extension)

        # Move and rename file to "folder"
        os.rename(book.image_location, new_location)
        book.image_location = new_location

        # Add book to author
        books.append(book)

        # Sort books by year
        books.sort(key=lambda x: x.year, reverse=True)

    def get_cover(self):
        # Get author image
        image_location = get_image("\"" + name + "\" author")

        # Get file extension
        file_extension = os.path.splitext(image_location)[-1]

        # All author images are named "folder"
        author.image_location = os.path.join(directory, "folder" + file_extension)

        # Move image to library author directory
        os.rename(image_location, author.image_location)
        
