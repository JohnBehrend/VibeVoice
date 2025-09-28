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
                txt = BeautifulSoup(
                    item.get_content().decode('utf-8')
                    .replace(u"\xa0","")
                    .replace(u"\u2019","'")
                    .replace(u"\u201c",'\t"')
                    .replace(u"\u2014"," - ")
                    .replace(u"\u2026","...")
                    .replace(u"\u201d",'"')
                    .replace(u"\u2018","'")
                    .replace(u"\u2013","-")
                    # spaces
                    .replace(u"\u0009","\t") # character tabulation
                    .replace(u"\u000A","\n") # line feed
                    .replace(u"\u000B"," ") # line tabulation
                    .replace(u"\u000C"," ") # form feed
                    .replace(u"\u000D","\n") # carriage return
                    .replace(u"\u0020"," ") # space
                    .replace(u"\u0085","\n") # next line
                    .replace(u"\u00A0"," ") # no-break space
                    .replace(u"\u1680"," ") # ogham space mark
                    .replace(u"\u180E"," ") # mongolian vowel separator
                    .replace(u"\u2000"," ") # en quad
                    .replace(u"\u2001"," ") # em quad
                    .replace(u"\u2002"," ") # en space
                    .replace(u"\u2004"," ") # three-per-em space
                    .replace(u"\u2005"," ") # four-per-em space
                    .replace(u"\u2006"," ") # six-per-em space
                    .replace(u"\u2007"," ") # figure space
                    .replace(u"\u2008"," ") # punctuation space
                    .replace(u"\u2009"," ") # thin space
                    .replace(u"\u200A"," ") # hair space
                    .replace(u"\u200B"," ") # zero width space
                    .replace(u"\u200C"," ") # zero width non-joiner
                    .replace(u"\u200D"," ") # zero width joiner
                    .replace(u"\u2028","\n ") # line separator
                    .replace(u"\u2029","\n\n") # paragraph separator
                    .replace(u"\u202F"," ") # narrow no-break space
                    .replace(u"\u205F"," ") # medium mathematical space
                    .replace(u"\u2060","-") # word joiner
                    .replace(u"\u3000"," ") # ideographic space
                    .encode('ascii')
                    , 'html.parser').get_text(separator=" ", strip=False)
                if txt.strip():  # Only add non-empty chapters
                    chapters.append(get_chapter_objs(txt))
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
    # print(f"Found {len(chapters)} chapters")
    
    # try to find characters that have quotes.
    #valid_speakers = {}
    previous_valid_speaker=None
    valid_context = []
    for i, chapter in enumerate(chapters):
        print(f"CHAPTER{i}")
        was_quote = False
        for j, chapter_obj in enumerate(chapter):
            if chapter_obj.has_quotes is False and was_quote is True:
                toks = chapter_obj.text.split(" ")
                if len(toks)>=2:
                    speaker, context = toks[:2]
                    if context in valid_context: # change speaker if we have good context
                        chapter[j-1].set_speaker(speaker)
                        print(speaker, '\n', chapter[j-1].text, '\n', chapter[j].text)
                    elif previous_valid_speaker is not None:
                        chapter[j-1].set_speaker(previous_valid_speaker)
                        print(speaker," INVALID context ", context, " using previous valid ", previous_valid_speaker, '\n', chapter[j-1].text, '\n', chapter[j].text)
                else: # not enough context keep same speaker
                    chapter[j-1].set_speaker(previous_valid_speaker)
                    print("NOT ENOUGH CONTEXT, SINGLE:","\n", chapter[j-1].text,"\n", chapter[j])
                #if speaker in valid_speakers.keys():
                #    valid_speakers[speaker]+=1
                #else:
                #    valid_speakers[speaker]=1
            if chapter_obj.has_quotes:
                was_quote = True
            else:
                was_quote = False
    #print("\n".join([str(x) for x in sorted(speaker_counts.items(), key=lambda x: x[1], reverse=True)]))
    # Print each chapter (you can modify this to output in different formats)
    for i, chapter in enumerate(chapters):
        #print(f"\n--- Chapter {i+1} ---")
        for j, chapter_obj in enumerate(chapter):
            pass#print(chapter_obj)
            #if (chapter_obj.has_quotes and chapter_obj.speaker == "narrator"):
            #    print("Speaker 2:", chapter_obj.text)
if __name__ == "__main__":
    main()
