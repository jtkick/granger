#!/usr/bin/env python3

from setuptools import setup, find_packages

setup (
    name = "Granger",
    version = "0.5",
    packages = find_packages(),
    install_requires=[
        'mutagen',
        'requests',
        'argparse',
        'google_images_download @ git+https://gitlab.com/jtkick/google-images-download.git'
    ],

    author = "Jared Kick",
    author_email = "jaredkick@gmail.com",
    description = "Scrapes and organizes audiobook files.",
    keywords = "book audiobook organize scrape",
)
