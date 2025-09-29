#!/usr/bin/env python3
"""
Simple Python script to parse an EPUB file into an array of chapters.
"""

import argparse
import sys
from parse_helper import valid_context_list, invalid_speaker_list, same_speaker_tokens, parse_epub_to_chapters
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
                # If we have quotes, only swap the speaker if it was unknonwn.
                if was_quote or next_valid_speaker is None:
                    temp = j
                    while(temp>0):
                        if chapter[temp].has_quotes:
                            if chapter[temp].get_speaker() != chapter_obj.get_speaker():
                                if chapter[temp].get_speaker() is not None:
                                    chapter_obj.set_speaker(chapter[temp].get_speaker())
                                    break
                        temp = temp-1
                else: # If we know the speaker, use it
                    chapter_obj.set_speaker(next_valid_speaker)
            elif chapter_obj.has_quotes is False:
                if len(toks)>=2: # can update prior chapters if we have context
                    # scan tokens one by one. Avoid adverbs, and find proper nouns.
                    speaker = None
                    for i, tok in enumerate(toks):
                        if i == 0:
                            continue
                        # navigate manually to find proper nouns as speakers
                        if tok.replace(",","").replace(".","").replace(";","") in valid_context_list:
                            if toks[i-1].endswith("ly"): # adverb
                                if (i>1) and len(toks[i-2])>0 and toks[i-2][0].isupper():
                                    speaker = toks[i-2].replace(",","").replace(".","").replace(";","").replace("'s","").replace("'","")
                            elif toks[i-1].lower() in same_speaker_tokens:
                                speaker = toks[i-1].lower()
                            elif len(toks[i-1])>0 and toks[i-1][0].isupper(): # proper noun
                                speaker = toks[i-1].replace(",","").replace(".","").replace(";","").replace("'s","").replace("'","")
                    if speaker is None:
                        pass # print(f"UNKNOWN SPEAKER from {toks}")
                    if speaker:
                        if speaker not in invalid_speaker_list: # Ignore He/she/we/they
                            if was_quote:
                                # print("**",speaker, " set to ",chapter[j-1])
                                chapter[j-1].set_speaker(speaker) # only update previous chapter if it was a quote
                            next_valid_speaker = speaker # but keep track of valid speakers for next quote
                        else:
                            next_valid_speaker = None
            was_quote = chapter_obj.has_quotes
    # # Try to detect sequential quotes and ensure that they have unique speakers.
    # prev_speaker=None
    # prev_other_speaker=None
    # for chapter in chapters:
    #     for i, chapter_obj in enumerate(chapter):
    #         if chapter_obj.has_quotes:
    #             speaker = chapter_obj.get_speaker()
    #             if (i>0):
    #                 # record prior speaker if it was different
    #                 if chapter[i-1].has_quotes:
    #                     prev_speaker = chapter[i-1].get_speaker()                
    #                     if prev_speaker != speaker:
    #                         prev_other_speaker = prev_speaker
    #                     elif prev_speaker == speaker:
    #                         print("SEQUENTIAL SPEAKER, NEEDS TO SWAP")
    #                         if prev_other_speaker is not None: # same speaker, so swap
    #                             print("UPDATE sequential", speaker, prev_speaker, prev_other_speaker)
    #                             chapter[i].set_speaker(prev_other_speaker)
    # Print each chapter (you can modify this to output in different formats)
    speaker_counts={}
    for i, chapter in enumerate(chapters[2:]):
        #print(f"\n--- Chapter {i+1} ---")
        for j, chapter_obj in enumerate(chapter):
            print(chapter_obj)
            this_speaker = str(chapter_obj.get_speaker())
            if this_speaker in speaker_counts.keys():
                speaker_counts[this_speaker]+=1
            else:
                speaker_counts[this_speaker]=1
        break
    print("\n".join([str(x) for x in sorted(speaker_counts.items(), key=lambda x: x[1], reverse=True)]))
    # print("SPEAKERS")
    # print(speakers)
if __name__ == "__main__":
    main()
