import auburn
import os
import re

PART_FINDER_REGEX_STRING = "(?:[Pp][AaRrTtSs]{0,7}[^a-zA-Z0-9]{0,5}(\d+)(?:[^0-9-thr\v]{0,5}(\d+)|\s+[\Dthru-]{0,5}\s+(\d+))?|[^a-zA-z]+(\d+)[^0-9-thr\v]{1,5}(\d+)|\s+[Cc][HhAaPpTtEeRrSs]{0,8}[^a-zA-Z0-9]*(\d+)(?:[^0-9]{0,5}(\d+))?(?:\s+[Pp][AaRrTtSs]{0,6}[^a-zA-Z0-9]{0,5}(\d+)(?:[\D\-through\v]{0,5}(\d+)\s)?)?)"

# This is that class that contains a file that is part of an Audiobook
class Audio_File:
    file_abs_path = ""
    title = ""
    # List of all high-level parts contained in this audio file
    high_parts = []
    # List of all chapters contained in this audio file
    chapters = []
    # List of all low-level parts contained in this audio file
    low_parts = []

    def __init__(self):
        self.file_abs_path = ""
        self.high_parts = []
        self.chapters = []
        self.low_parts = []

    def __init__(self, location):
        self.file_abs_path = location
        self.high_parts = []
        self.chapters = []
        self.low_parts = []

    # '<' operator for sorting        
    def __lt__(self, other):
        if self.high_parts < other.high_parts:
            return True
        elif self.chapters < other.chapters:
            return True
        elif self.low_parts < other.low_parts:
            return True
        else:
            return False
            
    def __str__(self):
        # Display current filename, and planned filename
        return (os.path.basename(self.file_abs_path) +
                " -> " +
                self.title +
                os.path.splitext(self.file_abs_path)[-1])
            
    # Sets the new filename from part and chapter numbers
    def set_title(self, book_title):
        # Start with book title
        self.title = book_title
        # Write part number
        if self.high_parts:
            if len(self.high_parts) == 1:
                self.title += " - Part " + self.high_parts[0]
            elif len(high_parts) > 1:
                self.title += " - Parts " + self.high_parts[0] + "-" + self.high_parts[-1]
        # Write chapter number
        if self.chapters:
            if len(self.chapters) == 1:
                self.title += " - Chapter " + self.chapters[0]
            elif len(high_parts) > 1:
                self.title += " - Chapters " + self.chapters[0] + "-" + self.chapters[-1]
        # Write low part number
        if self.low_parts:
            if len(self.low_parts) == 1:
                self.title += " - Part " + self.low_parts[0]
            elif len(self.low_parts) > 1:
                self.title += " - Parts " + self.low_parts[0] + "-" + self.low_parts[-1]
        
        
    # Uses the file_abs_path to get parts and chapters for organizing
    def get_parts(self):
        # Parse file_abs_path for matches
        matches = re.finditer(PART_FINDER_REGEX_STRING, self.file_abs_path, re.MULTILINE)
    
        # Initialize variables
        high_part_num = 0
        num_high_parts = 0
        end_high_part_num = 0
        chapter_num = 0
        end_chapter_num = 0
        low_part_num = 0
        num_low_parts = 0
        # Get values from regex matches
        for match in matches:
            # Group 4: Higher part number
            if match.group(4) is not None:
                high_part_num = match.group(4)
            # Group 1: Higher part number
            if match.group(1) is not None:
                high_part_num = match.group(1)
            # Group 5: Number of higher parts
            if match.group(5) is not None:
                num_high_parts = match.group(5)
            # Group 2: Number of higher parts
            if match.group(2) is not None:
                num_high_parts = match.group(2)
            # Group 3: End of higher part range
            if match.group(3) is not None:
                end_high_part_num = match.group(3)
            # Group 6: Chapter number
            if match.group(6) is not None:
                chapter_num = match.group(6)
            # Group 7: End of chapter range
            if match.group(7) is not None:
                end_chapter_num = match.group(7)
            # Group 8: Lower part number
            if match.group(8) is not None:
                low_part_num = match.group(8)
            # Group 9: Number of lower parts
            if match.group(9) is not None:
                num_low_parts = match.group(9)

        # Make sure part numbers are in correct order
        if high_part_num and num_high_parts:
            if high_part_num > num_high_parts:
                high_part_num, num_high_parts = num_high_parts, high_part_num
        if low_part_num and num_low_parts:
            if low_part_num > num_low_parts:
                low_part_num, num_low_parts = num_low_parts, low_part_num

        # Write numbers to member variables
        if high_part_num and end_high_part_num:
            # Make sure numbers are in correct order
            if high_part_num > end_high_part_num:
                # Swap variables
                high_part_num, end_high_part_num = end_high_part_num, high_part_num
            self.high_parts = list(range(high_part, end_high_part_num + 1))
        elif high_part_num:
            self.high_parts = [ high_part_num ]
            
        if chapter_num and end_chapter_num:
            # Make sure numbers are in correct order
            if chapter_num > end_chapter_num:
                # Swap variables
                chapter_num, end_chapter_num = end_chapter_num, chapter_num
            self.chapters = list(range(chapter_num, end_chapter_num + 1))
        elif chapter_num:
            self.chapters = [ chapter_num ]
            
        if low_part_num:
            self.low_parts = [ low_part_num ]

