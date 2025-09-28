#!/usr/bin/env python3
"""
Test module for parse_chapter.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from parse_chapter import get_chapter_objs

def test_single_paragraph():
    """Test with a single paragraph"""
    text = "This is a single paragraph of text without quotes."
    result = get_chapter_objs(text)
    
    assert len(result) == 1
    assert result[0].has_quotes == False
    assert result[0].speaker == "narrator"
    assert result[0].text == text
    print("✓ Single paragraph test passed")

def test_multiple_paragraphs():
    """Test with multiple paragraphs"""
    text = "First paragraph.\n\nSecond paragraph with \"quotes\".\n\nThird paragraph."
    result = get_chapter_objs(text)
    
    assert len(result) == 3
    assert result[0].has_quotes == False
    assert result[0].speaker == "narrator"
    assert result[0].text == "First paragraph."
    
    assert result[1].has_quotes == True
    assert result[1].speaker == "narrator"
    assert result[1].text == 'Second paragraph with "quotes".'
    
    assert result[2].has_quotes == False
    assert result[2].speaker == "narrator"
    assert result[2].text == "Third paragraph."
    print("✓ Multiple paragraphs test passed")

def test_empty_paragraphs():
    """Test with empty paragraphs"""
    text = "First paragraph.\n\n\n\nSecond paragraph."
    result = get_chapter_objs(text)
    
    assert len(result) == 2
    assert result[0].text == "First paragraph."
    assert result[1].text == "Second paragraph."
    print("✓ Empty paragraphs test passed")

def test_paragraph_with_single_quotes():
    """Test with single quotes"""
    text = "This is a paragraph with 'single quotes'."
    result = get_chapter_objs(text)
    
    assert len(result) == 1
    assert result[0].has_quotes == True
    print("✓ Single quotes test passed")

if __name__ == "__main__":
    test_single_paragraph()
    test_multiple_paragraphs()
    test_empty_paragraphs()
    test_paragraph_with_single_quotes()
    print("All tests passed!")
