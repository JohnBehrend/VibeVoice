#!/usr/bin/env python3
"""
Module to parse chapter content and return chapter objects.
"""

import re

class ChapterObj:
    def __init__(self, has_quotes: bool, speaker: str, text: str):
        self.has_quotes = has_quotes
        self.speaker = speaker
        self.text = text.strip()
    def _get_speaker_num(self):
        if self.has_quotes:
            return 2
        else:
            return 1

    def __str__(self):
        return f"Speaker {self._get_speaker_num()}: {self.text}"
    def get_speaker(self):
        return self.speaker
    def set_speaker(self, speaker:str):
        self.speaker = speaker

def get_chapter_objs(text: str):
    """
    Parse a chapter's text and return a list of chapter objects with the required properties.
    
    Args:
        text (str): The full text of the chapter
        
    Returns:
        list: List of ChapterObj objects with has_quotes, speaker, and text properties
    """
    # For now, set speaker to "narrator" as requested
    speaker = "narrator"
    
    # Split text into paragraphs (assuming paragraphs are separated by single newlines)
    paragraphs = text.split('\n')
    
    # Create a list of ChapterObj for each paragraph
    chapter_objs = []
    for paragraph in paragraphs:
        # Skip empty paragraphs
        if paragraph.strip():
            # If there are quotes, we need to split the paragraph to separate the quote from the rest
            if '"' in paragraph:
                # Find all quoted text in the paragraph
                quotes = [x.strip() for x in paragraph.split('"')]
                if paragraph.startswith('"'):# or paragraph.startswith("'"):
                    quote_en=True
                else:
                    quote_en=False
                for quote in quotes:
                    if len(quote)>0: 
                        chapter_objs.append(ChapterObj(quote_en, speaker, quote))
                    quote_en = not quote_en
            else:
                # No quotes, treat as normal paragraph
                chapter_objs.append(ChapterObj(False, speaker, paragraph))
    
    return chapter_objs
