#!/usr/bin/env python3
"""
Simple Python script to parse an EPUB file into an array of chapters.
"""

import argparse
import sys
from parse_helper import valid_context, same_speaker_tokens, parse_epub_to_chapters
from parse_chapter import ChapterObj

def main():
    parser = argparse.ArgumentParser(description="Parse an EPUB file into an array of chapters")
    parser.add_argument("epub_file", help="Path to the EPUB file")
    
    args = parser.parse_args()
    
    # Parse the EPUB file
    chapters = parse_epub_to_chapters(args.epub_file)
    
    if not chapters:
        print("No chapters found or error occurred")
        sys.exit(1)
    
    for i, chapter in enumerate(chapters):
        # print(f"CHAPTER{i}")
        was_quote = False
        next_valid_speaker=None
        for j, chapter_obj in enumerate(chapter):
            toks = chapter_obj.text.split(" ")
            if chapter_obj.has_quotes is True:
                # If we have quotes, only set the speaker if it was unknonwn.
                if chapter_obj.get_speaker() is None:
                    chapter_obj.set_speaker(next_valid_speaker)
                elif was_quote:
                    chapter_obj.swap_speaker() # update speaker for sequential quotes
            elif chapter_obj.has_quotes is False:
                if len(toks)>=2: # can update prior chapters if we have context
                    speaker = toks[0].lower().replace(",","").replace(".","").replace(";","").replace("'s","").replace("'","")
                    context = toks[1].lower().replace(",","").replace(".","").replace(";","")
                    if context in valid_context:
                        if speaker not in same_speaker_tokens: # Ignore He/she/we/they
                            if was_quote:
                                chapter[j-1].set_speaker(speaker) # only update previous chapter if it was a quote
                            else:
                                next_valid_speaker = speaker # but keep track of valid speakers for next quote
            was_quote = chapter_obj.has_quotes

    #print("\n".join([str(x) for x in sorted(speaker_counts.items(), key=lambda x: x[1], reverse=True)]))
    # Print each chapter (you can modify this to output in different formats)
    # speakers = set()
    for i, chapter in enumerate(chapters):
        #print(f"\n--- Chapter {i+1} ---")
        for j, chapter_obj in enumerate(chapter):
            print(chapter_obj)
            # speakers.add(chapter_obj.get_speaker())
    # print("SPEAKERS")
    # print(speakers)
if __name__ == "__main__":
    main()
