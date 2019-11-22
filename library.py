class Library:
    base_dir = ""
    authors = {}

    def __init__(self):
        pass

    def __init__(self, library_dir):
        if (os.path.isdir(library_dir)):
            self.base_dir = library_dir
        else:
            raise NotADirectoryError(library_dir + ": not a valid directory")

    # This function moves the audiobook and cover to pre-specified library location
    def add_book(self, book):
        # Get cover image
        if args.verbose:
            print("Downloading book cover...")
        book.get_cover()

        # Write tags to audio file
        if args.verbose:
            print("Writing audio file tags...")
        book.write_tags()

        # Create author if it doesn't exist
        add_author(book.author)
    
        # Add book to author
        authors[book.author].add_book(book)


    def add_author(self, name):
        # If author already exists, just return
        if name in authors:
            return

        # Otherwise create new author
        author = Author(base_dir, name)

        # Create path for author
        if not os.path.isdir(author.directory):
            os.mkdir(author.directory)

            # Get author image
            author.get_cover()

        # Add newly created author to library object
        authors[name] = author
