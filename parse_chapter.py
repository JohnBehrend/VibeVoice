#!/usr/bin/env python3
"""
Module to parse chapter content and return chapter objects.
"""

import re

class ChapterObj:
    def __init__(self, has_quotes: bool, text: str, speaker, prev):
        self.has_quotes = has_quotes
        self.speaker = speaker # speaker can be either a string or a reference to prior ChapterObj
        self.text = text.strip()
        self.prev = prev
    def _get_speaker_num(self):
        if self.has_quotes:
            return 2
        else:
            return 1

    def __str__(self):
        #return f"Speaker {self._get_speaker_num()}: {self.text}"
        return f"Speaker {int(self.has_quotes)}: ({self.get_speaker()})  {self.text}"
    def get_speaker(self):
        # If we have a speaker reference and it's a ChapterObj, resolve it
        if self.speaker is None:
            return self.speaker
        elif isinstance(self.speaker, ChapterObj):
            return self.speaker.get_speaker()
        else:
            return self.speaker
    def set_speaker(self, speaker):
        # Allow speaker to be either a string or another ChapterObj
        self.speaker = speaker

    def set_last_other_valid_speaker(self):
        # use link to prev to get the last chapter obj with has_quotes=True.
        # ignores the first match.
        self.speaker = self.prev.get_last_other_valid_speaker()

    def set_last_valid_speaker(self):
        # use link to prev to get the last chapter obj with has_quotes=True
        self.speaker = self.prev.get_last_valid_speaker()

    def get_last_other_valid_speaker(self):
        """Recursively look at prev ChapterObj for the next one with has_quotes=True, but skip the first."""
        if self.prev is None:
            return None
        if self.has_quotes:
            return self.prev.get_last_valid_speaker()
        else:
            return self.prev.get_last_other_valid_speaker()
        
    def get_last_valid_speaker(self):
        """Recursively look at prev ChapterObj for the next one with has_quotes=True."""
        if self.prev is None:
            return None
        if self.has_quotes:
            return self
        else:
            return self.prev.get_last_valid_speaker()

def get_chapter_objs(text: str):
    """
    Parse a chapter's text and return a list of chapter objects with the required properties.
    
    Args:
        text (str): The full text of the chapter
        
    Returns:
        list: List of ChapterObj objects with has_quotes, speaker, and text properties
    """
    # Split text into paragraphs (assuming paragraphs are separated by single newlines)
    paragraphs = text.split('\n')
    
    # Create a list of ChapterObj for each paragraph
    chapter_objs = []
    prev = None
    for paragraph in paragraphs:
        # Skip empty paragraphs
        if paragraph.strip():
            # If there are quotes, we need to split the paragraph to separate the quote from the rest
            if '"' in paragraph:
                # Find all quoted text in the paragraph
                quotes = [x.strip() for x in paragraph.split('"')]
                if paragraph.startswith('"'):
                    quote_en=True
                else:
                    quote_en=False
                for quote in quotes:
                    if len(quote)>0:
                        chapter_objs.append(ChapterObj(quote_en,  quote, None, prev))
                        prev = chapter_objs[-1]
                    quote_en = not quote_en
            else:
                # No quotes, treat as normal paragraph
                chapter_objs.append(ChapterObj(False, paragraph, None, prev))
                prev = chapter_objs[-1]
    return chapter_objs
