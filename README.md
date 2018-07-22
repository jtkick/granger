# Auburn

Auburn is a personal project to create an automated audiobook organizer and scraper.

It is meant to be a layer between youtube-dl and Plex to make downloading and adding audiobooks to my Plex server fully automated and painless. The program will guess a title based solely on the filename, rewrite the tags and filename, download the appropriate cover art for each audiobook, and move it to the specified location given in the config file.

This is my first project outside of academia and my first ever Python project, so it is not expected to be perfectly stable for awhile. Any critiques or contributions are welcome.

# Usage

To use Auburn, simply call:

> $ ./auburn.py /path/to/audiobook/files/

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

> $ git clone 