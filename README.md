<div align="center">
  <a href="https://gitlab.com/jtkick/granger/">
      <img src="granger.png" width="120" height="120"/>
  </a>
  
  <h1 align="center">Granger</h1>

  <p align="center">
    Organize and scrape metadata for audiobooks.
    <br />
    <br />
    <a href="https://gitlab.com/jtkick/granger/">Documentation</a>
    ·     
    <a href="https://gitlab.com/jtkick/granger/issues">Report Bug</a>


  </p>
  
</div>

## Table of Contents
* [About](#about)
* [Setup](#setup)
  * [Installation](#installation)
  * [Configuration](#configuration)
* [Usage](#usage)
* [Contributing](#contributing)
  * [New Features](#new-features)
  * [Bugs](#bugs)
  * [Donating](#donating)


## About

Granger is a personal project to create an automated audiobook organizer and scraper.

It is meant to be a layer between youtube-dl and Plex to make downloading and adding audiobooks to my Plex server fully automated and painless. The program will guess a title based solely on the filename, rewrite the tags and filename, download the appropriate cover art for each audiobook, and move it to the specified location given in the AUDIOBOOK_DIR variable.

This is my first project outside of academia and my first ever Python project, so it is not expected to be very robust for awhile. Any critiques or contributions are welcome.

## Setup

#### Installation

Clone git repository

    git clone https://gitlab.com/jtkick/granger.git
    cd ./granger

Run install script

    setup ./setup.py install
    
#### Configuration
    
In order to properly import new audiobooks, the 'AUDIOBOOK_DIR' variable must be set in your 'config.py' file. This should be the abolute path of the directory you want to import your books to, for example:

    AUDIOBOOK_DIR=/home/user/Audiobooks/

## Usage

To use Granger, run the following command, where '/path/to/new/audiobook/files/' is a directory containing all audio files you want to import to your audiobook library.

    ./granger.py /path/to/new/audiobook/files/

The program will iterate through all the files in the given directory and process them one by one. 


## Contributing

Anybody is welcome to contribute so long as they do so politely and respectfully.

#### New Features

1. Fork the project
2. Create new branch

    `git checkout -b feature/new_feature`
3. Commit your changes

    `git commit -m 'Added new feature.'`
4. Push to repository

    `git push origin feature/new_feature`
5. Create new merge request

#### Bugs

If you cannot contribute code, consider reporting bugs by [submitting new issue](https://gitlab.com/jtkick/granger/issues).

#### Donating

If this project help you reduce time to develop, you can give me a cup of coffee :) 

[![paypal](https://www.paypalobjects.com/en_US/i/btn/btn_donateCC_LG.gif)](https://www.paypal.com/cgi-bin/webscr?cmd=_donations&business=N3R7EGLD32ZQ8&currency_code=USD&source=url)
