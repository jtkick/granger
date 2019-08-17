#!/usr/bin/env python

# For using the Google Book API
import requests
# For manipulating API responses
import json
# For comparing titles after Google Books API search
#import Levenshtein
import difflib

TITLES = [
    # Titles to test accuracy of Levenshtein ratio
    # Intentionally includes non-books to see where results start to break down
    "2001 - A Space Odyssey Audiobook _ Arthur C. Clarke.ogg",
    "Astrophysics for People in a Hurry - Neil deGrasse Tyson Bestseller Science Audiobook",
    "How audiobooks are recorded",
    "Deep Work Rules for Focused Success in a Distracted World Audiobook ",
    "Rick Riordan Audiobook the Red Pyramid (The Kane Chronicles, Book 1) ",
    "(Full Audiobook) This Book Will Change Everything! (Amazing!)",
    "20.000 Leagues Under the Sea - Jules Verne [Audiobook]",
    "The Wr0ng Side 0f G00dBye(audio-book) by Michael Connelly",
    "GRIMM'S FAIRY TALES by the Brothers Grimm - FULL Audio Book | GreatestAudioBooks.com",
    "How to Talk to Anyone: 92 Little Tricks for Big Success in Relationships Audiobook Part 1",
    "Fight Club Audiobook",
    "THE ART OF WAR - FULL Audio Book by Sun Tzu (Sunzi) - Business & Strategy Audiobook | Audiobooks",
    "TREASURE ISLAND - FULL AudioBook by Robert Louis Stevenson - Adventure / Pirate Fiction",
    "How To Get FREE Audiobook of any Book (HINDI) किसी भी बुक का ऑडियोबुक पाए बिलकुल फ्री ",
    "Warhammer, Old Earth Audiobook,To The Gates Of Terra ",
    "Audiobook I Am Legend 1 by Richard Matheson #Audiobook",
    #lol
    "(FULL Audiobook) The Book Of Hidden Knowledge! (Don't Listen If You Aren't Ready!) ",
    "American Indian Fairy Tales Audiobook ",
    "TPAudiobook | Me Talk Pretty One Day AUDIO BOOK By David Sedaris",
    "The Chrysalids 1955 by John Wyndham Full Audiobook © by EkerTang ",
    "The Butcher: Anatomy of a Mafia Psychopath 1 Audiobooks #1 * Philip Carlo ",
    "Alan Partridge: Nomad Audiobook Biography Theatre & Performance Art",
    "Haricharitramrut Sagar Katha Audio Book Pur 1 Tarang 30",
    "The Children of Odin [Norse Mythology Audiobook] Thor, Loki, Asgard, Valhalla",
    "So...You want to be an audiobook narrator?",
    "The Wonder Weeks AudioBook App - SAMPLE",
    "Holy Bible Audio: Book of Revelation - Full (Contemporary English)",
    "LEO TOLSTOY ANNA KARENINA audiobook part1. Russian classics",
    "Audiobook: Notes from the Underground by Fyodor Dostoevsk",
    "The Auschwitz Volunteer Audiobook, Interview with the Narrator",
    "WHERE TO GET AUDIOBOOKS | A Guide to Audiobooks",
    "The Secret Garden Audiobook-Frances Hodgson Burnette-Childrens Story-Audio Book-Kids Stories ",
    "The Kybalion of Hermes Trismegistus, [FULL Audiobook] (+ Emerald Tablet)",
    "Victor Hugo — The Hunchback of Notre-Dame. Book 7 (Free Audiobook of Classical Literature) ",
    "Digital Audiobook Rentals ",
    "Software is Elementary Free Audiobook ",
    "Wild Animals I Have Known Audiobook Ernest Thompson SETON",
    "Teaser - A Good Audiobook Speaks Volumes ",
    "Kho sách nói | Cà phê cùng TONY | Tony buổi sáng |audio book dạy tư duy kinh doanh làm giàu hay nhất",
    "Make Knitting Time Reading Time - Listen to an Audiobook",
    "Nuôi Con Không Phải Là Cuộc Chiến (audiobook)",
    "TWELVE YEARS A SLAVE by Solomon Northup - FULL Audio Book | Greatest Audio Books 12",
    "\"Sekretne życie drzew\" | audiobook",
    "Smart Audiobook Player",
    "Self Reliance, by Ralph Waldo Emerson, Essay Audiobook, Classic Literature",
    # Seriously? Why?
    "Children's audiobook - The Jungle book - Full audiobook English subtitle 🌴🌴🌲🌳🎄🙉🙉",
    "A Christmas Album Free Audiobook",
    "Zanoni | Edward Bulwer-Lytton | *Non-fiction, General Fiction, Philosophy | Audio Book | 9/9",
    "Audio Book: The Fire Next Time by James Baldwin read by Jesse L. Martin",
    "Anne's House of Dreams by Lucy Maud Montgomery Free Full Audio Book",
    "\"Dawca przysięgi II\" | audiobook",
    "The Story of My Life (Audio Book) by Helen Keller (1888-1968) (1/2)",
    "Top 5 Audiobook Apps of 2018",
    "ARE AUDIOBOOKS CONSIDERED \"REAL READING\"?",
    "Genesis - King James Bible, Old Testament (Audio Book)",
    "Peter Pan fairytale - audiobook (Learning English - Elementary)",
    "The Raven (Christopher Lee)",
    "THINGS TO DO WHILE AUDIOBOOKING",
    "Audiobooks and English",
    "SCREENWRITER INTERVIEW: Steve Herold \"Death of An Umbrella Salesman\" | GreatestAudioBooks",
    "HOLY BIBLE: EPHESIANS by The Apostle Paul (W.E.B.) - FULL AudioBook | GreatestAudioBooks",
    "MACBETH - Audiolibro en español | by William Shakespeare | GreatestAudioBooks",
    "BEAUTY & THE BEAST - FULL AudioBook | GreatestAudioBooks",
    "THE YOGA SUTRAS OF PANTANJALI - FULL AudioBook | GreatestAudioBooks.com",
    "Bhagavad-Gîtâ - FULL AudioBook | GreatestAudioBooks.com",
    "Bhagavad-Gîtâ",
    "COLLECTED ARTICLES OF FREDRICK DOUGLASS - FULL AudioBook | GreatestAudioBooks.com",
    "COLLECTED ARTICLES OF FREDRICK DOUGLASS",
    "وداع وطن | محمود سامي البارودي - مصر | ALWATAN - FULL AudioBook | Greatest Audio Books",
    "وداع وطن | محمود سامي البارودي - مصر",
    "ごんぎつね: 新美 南吉 (Gongitsune) Nankichi Niimi - FULL AudioBook | 日本人 Nipponjin オーディオブック Ōdiobukku",
    "Yoga Sutras of Patanjali: The Book of the Spiritual Man (FULL Audiobook)"
]

SUCCESS = []
FAILURE = []

# Words to remove that tend to appear in file names but don't describe the book
# These words (especially "audiobook") tend to screw up Google Books searches
WORDS = ["audiobooks", "audiobook", "audio", "book", " by ", "narrated", "full", "complete", "hd", "pdf", "abridged", "unabridged", "subtitles", ".com", ".net", ".org", "mp3", "mp4", "m4v", "m4a", "m4b", "wav", "wmv"]

# Special characters to remove from filename. '&' and ''' are NOT removed as these are sometimes helpful
SPEC_CHARS = ['~', '`', '@', '$', '%', '^', '*', '_', '=', '<', '>', '(', ')', '[', ']', '{', '}', '\"', '|', '\\', '+', '-', ':', '#', '/', '!', '?', ',', '.']

# Used to find similarity between filename and results from Google Books API
def jaccard_similarity(list1, list2):
    s1 = set(list1)
    s2 = set(list2)
    return len(s1.intersection(s2)) / len(s1.union(s2))

def main():

    # Iterate through list
    for audio_file in TITLES:

        # Get filename
        search_term = audio_file

        # We will work with lowercase strings
        search_term = search_term.lower()

        search_term.replace("excerpt", '')

        # Remove unhelpful words
        for word in WORDS:
            search_term = search_term.replace(word, ' ')

        # Remove special characters
        for char in SPEC_CHARS:
            search_term = search_term.replace(char, '')

        # Search Google Books API
        response = requests.get("https://www.googleapis.com/books/v1/volumes?q=" +
                            search_term.replace(' ', '+'))

        # Make JSON response readable
        #response = json.loads(response)

        response = response.json()

        # Compare titles by iterating through titles and seeing which ones match original
        # While Google Books search is good, occasionally it returns books that are 
        # clearly not a match, so we will crosscheck the result with the original string
        # and see which one is the closest
        # For now we will use the Levenshtein algorithm to compute similarity

        match = ""
        ratio = 0.0
        if "items" in response:
            for item in response["items"]:
                response_str = ""
                if "title" in item["volumeInfo"]:
                    response_str += item["volumeInfo"]["title"]
                if "authors" in item["volumeInfo"]:
                    response_str += " "
                    response_str += item["volumeInfo"]["authors"][0]
                response_str = response_str.lower()
                print(search_term)
                print(response_str)
                print()
                test_ratio = jaccard_similarity(search_term.split(), response_str.split())
                if test_ratio > ratio:
                    match = item["volumeInfo"]
                    ratio = test_ratio

                response_str = ""
                if "title" in item["volumeInfo"]:
                    response_str += item["volumeInfo"]["title"]
                if "subtitle" in item["volumeInfo"]:
                    response_str += " " + item["volumeInfo"]["subtitle"]
                if "authors" in item["volumeInfo"]:
                    response_str += " " + item["volumeInfo"]["authors"][0]
                response_str = response_str.lower()
                print(search_term)
                print(response_str)
                print()
                test_ratio = jaccard_similarity(search_term.split(), response_str.split())
                if test_ratio > ratio:
                    match = item["volumeInfo"]
                    ratio = test_ratio

        # Keep an eye on what Google response is
        print("Filename: " + audio_file)
        print("Search term: " + search_term)
        print("Google says:")
        if "title" in match:
            print("Title:    " + match["title"])
        if "subtitle" in match:
            print("Subtitle: " + match["subtitle"])
        if "authors" in match:
            print("Author:   " + match["authors"][0])
        print("")

        correct = ""
        while (correct != 'Y' and
               correct != 'y' and
               correct != 'N' and
               correct != 'n'): 
            correct = input("Is this correct (y/n)? ")
        if correct == 'Y' or correct == 'y':
            SUCCESS.append(ratio)
        else:
            FAILURE.append(ratio)

    # Print successes and failures
    print("SUCCESSES")
    SUCCESS.sort()
    for ratio in SUCCESS:
        print(str(ratio))

    print("\nFAILURES")
    FAILURE.sort()
    for ratio in FAILURE:
        print(str(ratio))

if __name__ == "__main__":
    main()