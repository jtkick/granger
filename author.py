class Author:

    # Directory of author relative to the library root directory
    # In most cases this will be the same as the author name
    directory = ""
    # Name of the author
    name = ""
    # Should contain only 'audiobook' objects in chronological order
    books = []

    def __init__(self, author_name):
        self.name = author_name
        self.directory = author_name

    # Add book will update the 'books' list as well as move the audiobook and cover files to
    # the proper directory
    # This function should only be called by library.add_book() which will do the thinking
    # and is called in the main function.
    def add_book(self, book):
        # Add book to author
        books.append(book)

        # Sort books by year
        books.sort(key=lambda x: x.year, reverse=True)

    # Returns true if book of the given name is already in the library under this author
    def has_book(self, title):
        for book in books:
            if book.title == title:
                return True
        return False