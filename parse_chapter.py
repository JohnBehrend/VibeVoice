#!/usr/bin/env python3
"""
Module to parse chapter content and return chapter objects.
"""

import re

class ChapterObj:
    def __init__(self, has_quotes: bool, speaker: str, text: str):
        self.has_quotes = has_quotes
        self.speaker = speaker
        self.text = text

    def __str__(self):
        return f"Speaker: {self.speaker}\nHas Quotes: {self.has_quotes}\nText: {self.text}"

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
            # Check if there are quotations in the paragraph
            has_quotes = any(x in paragraph.replace("'s","") for x in ["'",'"'])
            
            # If there are quotes, we need to split the paragraph to separate the quote from the rest
            if has_quotes:
                # Find all quoted text in the paragraph
                # This regex will match both single and double quoted strings
                quotes = re.split("[\"']", paragraph.replace("'s",'QUOTED_S').replace("'ve","QUOTED_VE"))
                if paragraph.startswith('"') or paragraph.startswith("'"):
                    quote_en=True
                else:
                    quote_en=False
                for quote in quotes:
                    chapter_objs.append(ChapterObj(quote_en, speaker, quote.replace("QUOTED_S","'s").replace("QUOTED_VE","'ve")))
                    quote_en = not quote_en
            else:
                # No quotes, treat as normal paragraph
                chapter_objs.append(ChapterObj(has_quotes, speaker, paragraph))
    
    return chapter_objs
