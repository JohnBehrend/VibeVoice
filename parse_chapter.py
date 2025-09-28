#!/usr/bin/env python3
"""
Module to parse chapter content and return chapter objects.
"""

class ChapterObj:
    def __init__(self, has_quotes: bool, speaker: str, text: str):
        self.has_quotes = has_quotes
        self.speaker = speaker
        self.text = text

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
    
    # Split text into paragraphs (assuming paragraphs are separated by double newlines)
    paragraphs = text.split('\n\n')
    
    # Create a list of ChapterObj for each paragraph
    chapter_objs = []
    for paragraph in paragraphs:
        # Skip empty paragraphs
        if paragraph.strip():
            # Check if there are quotations in the paragraph
            has_quotes = '"' in paragraph or "'" in paragraph
            chapter_objs.append(ChapterObj(has_quotes, speaker, paragraph))
    
    return chapter_objs
