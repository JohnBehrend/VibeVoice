#!/usr/bin/env python3
"""
Simple Python script to parse an EPUB file into an array of chapters.
"""

import argparse
import sys
import os
from parse_chapter import valid_context_list, invalid_speaker_list
from parse_chapter import same_speaker_tokens, parse_epub_to_chapters
from parse_chapter import speaker_map
from demo.inference_from_file import main

def parse_epub():
    parser = argparse.ArgumentParser(description="Parse an EPUB file into an array of chapters")
    parser.add_argument("epub_file", help="Path to the EPUB file")
    parser.add_argument("--speaker_histogram", action="store_true", help="Print out a histogram of speakers.")
    parser.add_argument("--by_chapter", action="store_true", help="Save a file per chapter in a new folder labled chapters")
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
                        if speaker not in invalid_speaker_list+[x for x in same_speaker_tokens if x not in ["she","her"]]: # Ignore He/she/we/they
                            if was_quote:
                                # print("**",speaker, " set to ",chapter[j-1])
                                chapter[j-1].set_speaker(speaker) # only update previous chapter if it was a quote
                            next_valid_speaker = speaker # but keep track of valid speakers for next quote
                        else:
                            next_valid_speaker = None
            was_quote = chapter_obj.has_quotes

    # Print each chapter (you can modify this to output in different formats)
    speaker_counts={}
    if not os.path.isdir("./chapters") and args.by_chapter:
        os.mkdir("./chapters")
    for i, chapter in enumerate(chapters):
        #print(f"\n--- Chapter {i+1} ---")
        if args.by_chapter:
            with open(f"./chapters/chapter_{str(i).zfill(2)}.txt", "w") as f:
                for j, chapter_obj in enumerate(chapter):
                    f.write(str(chapter_obj)+"\n")
            main(
                other_args=argparse.Namespace(
                model_path="Jmica/VibeVoice7B",
                speaker_names=["John","Frank","Alice","Travis"],
                device="cuda",
                cfg_scale=1.4,
                output_dir="./chapters/",
                txt_path=f"./chapters/chapter_{str(i).zfill(2)}.txt"))
        else:
            print(chapter_obj)
        if args.speaker_histogram:
            this_speaker = str(chapter_obj.get_speaker())
            if this_speaker in speaker_counts.keys():
                speaker_counts[this_speaker]+=1
            else:
                speaker_counts[this_speaker]=1
        # break
    print("\n".join([str(x) for x in sorted(speaker_counts.items(), key=lambda x: x[1], reverse=True)]))
    # print("SPEAKERS")
    # print(speakers)
if __name__ == "__main__":
    parse_epub()
