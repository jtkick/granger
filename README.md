# Auburn

Auburn is a personal project to create an automated audiobook organizer and scraper.

It is meant to be a layer between youtube-dl and Plex to make downloading and adding audiobooks to my Plex server fully automated and painless. The program will guess a title based solely on the filename, rewrite the tags and filename, download the appropriate cover art for each audiobook, and move it to the specified location given in the AUDIOBOOK_DIR variable.

This is my first project outside of academia and my first ever Python project, so it is not expected to be very robust for awhile. Any critiques or contributions are welcome.

# Usage

To use Auburn, simply call:

> $ ./auburn.py /path/to/new/audiobook/files/

The program will iterate through all the files in the given directory and process them one by one. It is only designed to handle .ogg files, but will likely work with other major audio containers. There is no support for multi-file books yet.

# Installation

Install Google Images Downloader to download cover art

> $ pip install google_images_download

Install Requests to handle Google Books API response

> $ pipenv install requests

Install Levenshtein package to compare strings

> $ pip install python-Levenshtein

Install Mutagen to write audio file tags

> $ pip install mutagen

Clone repository

> $ git clone https://gitlab.com/jtkick/Auburn.git







Database Structure

*Each library has it's own file

Library --------------------------
    |
    |-> base_directory
    |
    |-> list of authors --------
        |
        |-> list of books
        
        
## Donation
If this project help you reduce time to develop, you can give me a cup of coffee :) 

[![paypal](https://www.paypalobjects.com/en_US/i/btn/btn_donateCC_LG.gif)](https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=A8YE92K9QM7NA)
