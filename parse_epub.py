#!/usr/bin/env python3
"""
Simple Python script to parse an EPUB file into an array of chapters.
"""

import argparse
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import sys
from parse_chapter import get_chapter_objs

def parse_epub_to_chapters(epub_path):
    """
    Parse an EPUB file into an array of chapters.
    
    Args:
        epub_path (str): Path to the EPUB file
        
    Returns:
        list: Array of chapter texts
    """
    try:
        book = epub.read_epub(epub_path)
        chapters = []
        
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                # Extract text content from HTML
                txt = BeautifulSoup(item.get_content(), 'html.parser').get_text(separator=" ", strip=False)
                if txt.strip():  # Only add non-empty chapters
                    chapters.append(txt)
                    chapter_objs = get_chapter_objs(txt)
                    for chapter_obj in chapter_objs:
                        print(chapter_obj.has_quotes)
                        print(chapter_obj.speaker)
                        print(chapter_obj.text)
                    exit()
        return chapters
    
    except Exception as e:
        print(f"Error parsing EPUB file: {e}")
        return []

def main():
    parser = argparse.ArgumentParser(description="Parse an EPUB file into an array of chapters")
    parser.add_argument("epub_file", help="Path to the EPUB file")
    
    args = parser.parse_args()
    
    # Parse the EPUB file
    chapters = parse_epub_to_chapters(args.epub_file)
    
    if not chapters:
        print("No chapters found or error occurred")
        sys.exit(1)
    
    # Print the number of chapters found
    print(f"Found {len(chapters)} chapters")
    
    # Print each chapter (you can modify this to output in different formats)
    for i, chapter in enumerate(chapters):
        print(f"\n--- Chapter {i+1} ---")
        print(chapter[:200] + "..." if len(chapter) > 200 else chapter)

if __name__ == "__main__":
    main()
