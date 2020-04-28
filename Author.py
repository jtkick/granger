import config as config
import os
import auburn
import shutil
import mutagen

class Author:

    # Absolute path of the author
    # In most cases this will be the same as the author name
    directory = ""
    image_location = None
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
    def add_book(self, book, delete):
        # TODO: FIX THE AWFUL LOGIC IN THIS FUNCTION
    
        book.directory = os.path.join(self.directory, book.title)

        # Make sure book directory exists
        if not os.path.isdir(book.directory):
            os.mkdir(book.directory)

        # Move/copy/delete audio files
        for audio_file in book.audio_files:
            # Get original file extension
            ext = os.path.splitext(audio_file.file_abs_path)[-1]
            
            # Define where the file will go and be named
            new_location = os.path.join(book.directory, (audio_file.title + ext))
            
            # Means we will add new book to library
            add = False
            # Move audio file
            if os.path.isfile(new_location):
                # If the book already exists in the library, do one of the following
                if config.OVERWRITE == "bitrate":
                    old_file = mutagen.File(new_location)
                    new_file = mutagen.File(audio_file.file_abs_path)
                    # If new file's bitrate is higher, remove the old file
                    if new_file.info.bitrate > old_file.info.bitrate:
                        # Remove old file and add new file
                        add = True

                elif config.OVERWRITE == "size":
                    # If new file is bigger, remove the old file
                    if os.path.getsize(audio_file.file_abs_path) > os.path.getsize(new_location):
                        # Remove old file and add new file
                        add = True
                elif config.OVERWRITE == "always":
                    # Remove old file and add new file
                    add = True
                elif config.OVERWRITE != "never":
                    print("Invalid value for \"OVERWRITE\" in configuration file.")
                    raise ValueError
            # File doesn't already exist, so add it
            else:
                add = True
            
            if delete and add:
                # Move file
                shutil.move(audio_file.file_abs_path, new_location)
                
                # Update file path
                audio_file.file_abs_path = new_location
                
            elif not delete and add:
                # Copy file
                shutil.copy2(audio_file.file_abs_path, new_location)
                
                # Update file path
                audio_file.file_abs_path = new_location
                
            else:
                return

        # Get image file location
        if book.image_location:
            file_extension = os.path.splitext(book.image_location)[-1]

            # Set new location of image file
            new_location = os.path.join(book.directory, "cover" + file_extension)

            # Move and rename file to "folder"
            shutil.move(book.image_location, new_location)
            book.image_location = new_location

        # Add book to author
        self.books.append(book)

        # Sort books by year
        self.books.sort(key=lambda x: x.year, reverse=True)

    def get_cover(self):
        # Get author image
        image_location = auburn.get_image("\"" + self.name + "\" author")

        if image_location:
            # Get file extension
            file_extension = os.path.splitext(image_location)[-1]

            # All author images are named "folder"
            self.image_location = os.path.join(self.directory, "folder" + file_extension)

            # Move image to library author directory
            shutil.move(image_location, self.image_location)
        
