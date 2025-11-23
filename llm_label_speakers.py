#!/usr/bin/env python3
"""
Module to take a chapter and automate sending through LLM for labeling characters.
"""
import argparse
import os
import sys
import json
from collections import Counter
from openai import OpenAI
# from unsloth import FastLanguageModel
# from transformers import AutoModelForCausalLM, AutoTokenizer
# import torch

# MODEL_PATH = "D:/models/unsloth/GLM-4.5-Air-GGUF"#"D:/models/lmstudio-community/gpt-oss-20b-GGUF"
# MODEL_GGUF = "GLM-4.5-Air-Q4_K_S-00001-of-00002.gguf"#"gpt-oss-20b-MXFP4.gguf"
#""
#"D:/models/unsloth/GLM-4.5-Air-GGUF"#/#"unsloth/glm-4.5-air-q4"#"unsloth/GLM-4.5-Air-GGUF"#"zai-org/GLM-4.5"
# /opt/model-storage/GLM-4.5-Air-UD-Q4_K_XL-00001-of-00002.gguf

def add_quotes_around_keys(json_body):
    """For some json text, we don't have quotes around keys. Example:
    char_map : {1: "narrator", 2: "char1", 3: "char2", 4: "char3"}
    ->
    char_map : {"1": "narrator", "2": "char1", "3": "char2", "4": "char3"}    
    """
    entries = []
    for entry in json_body.replace("{","").replace("}","").split(","):
        k,v = entry.split(":")
        k = k.strip()
        v = v.strip()
        if '"' not in k:
            k = '"'+k+'"'
        if '"' not in v:
            v = '"'+v+'"'
        entries.append(k+": "+v)
    #print("revised quotes to")
    revised_json_body = "{"+", ".join(entries)+"}"
    # print(revised_json_body)
    return revised_json_body

def interpret_result(result, attempt_num):
    """Process result of a LLM query of the following format:
-----
char_map : {"1": "narrator", "2": "First Character", "3": "Second Character"}
7:2
9:2
11:2
13:3
15:3
-----
      return character_map, line_map"""
    line_map = {}
    char_map = {}
    IN_CHARMAP = False
    MISSING_OPEN = False
    for line in result:
        if len(char_map) > 0:
            if ":" in line and not (line.startswith("#") or line.startswith("`") or line.startswith("*")):
                try:
                    this_line, speaker_num = line.split(":")
                    this_line = this_line.replace("Line ","").replace("Lines ","").replace("- ", "")
                    if "-" in this_line:
                        line_start, line_stop = this_line.split("-")
                        for x in range(int(line_start),int(line_stop)+1):
                            line_map[int(x)] = int(speaker_num)
                    else:
                        line_map[int(this_line)] = int(speaker_num)
                except:
                    print(f"INVALID SPEAKER FORMAT FROM LLM RUN {attempt_num}: {line}", file=sys.stderr)
        elif IN_CHARMAP:
            if MISSING_OPEN:
                if "{" in line:
                    MISSING_OPEN=False
                    json_body = line.strip()
            else:
                json_body = json_body+line.strip()
            if "}" in line:
                IN_CHARMAP=False
                print("TRYING MULTLINE CHARMAP:", json_body)
                try:
                    char_map = json.loads(json_body)
                except:
                    char_map = json.loads(add_quotes_around_keys(json_body))
        else:
            if ("char_map" in line) and ("{" in line) and ("}" in line):
                json_body = "{" + line.split("{")[1]
                try:
                    char_map = json.loads(json_body)
                except:
                    char_map = json.loads(add_quotes_around_keys(json_body))
            elif ("char_map" in line) and ("{" in line):
                IN_CHARMAP=True
                json_body = "{"
            elif "char_map" in line:
                IN_CHARMAP=True
                MISSING_OPEN=True
            # could eventually add a check for """json""" with unquoted keys.
    for k in char_map.keys():
        char_map[k] = (char_map[k].split("/")[0]).split(" (")[0].lower().strip().replace("‑","")
    # convert keys to int
    char_map = {int(k): v for k,v in char_map.items()}
    # remove line_map entries that are invalid.
    line_map = {line_num: char_num for line_num, char_num in line_map.items() if char_num in char_map.keys()}
    return char_map, line_map

def merge_line_maps(line_maps, verbose=False):
    """Take multiple line maps and determine the most common mapping for each line.
    If there is only one value for a line, we will pick that value.
    If there are two values for a line, we'll pick the first.
    If there more than two values for a line pick the majority. If all different pick first.
    """
    merged_line_map = {}# line_maps[0].copy()
    if len(line_maps)>0:
        for line_map in line_maps:
            for line, speaker_num in line_map.items():
                if not (line in merged_line_map.keys()):
                    merged_line_map[line] = [speaker_num]
                else:
                    merged_line_map[line].append(speaker_num)
    if verbose:
        print("Merged Line Map:")
        print(merged_line_map)
    return { k: Counter(v).most_common(1)[0][0] for k,v in merged_line_map.items()}
    
PROMPT_TXT = """
Prompt: Audiobook Dialogue Annotation Expert

You are an expert in audiobook dialogue annotation. Your task is to identify all speakers in a given chapter and provide detailed attribution for each quoted line.

Step-by-Step Instructions:

1. Character Identification: Scan the entire text and identify ALL characters (including narrator)
- Create a char_map with numbers starting from 1
- Include narrator as character 1
- Format: char_map : {1: "narrator", 2: "Character Name", ...}
- Use simple names when possible.

2. Quoted lines: Find each full line surrounded by double quotation marks.
- Find ALL lines that start AND end with double quotation marks ("). These will likely have multiple sentences each.

3. Speaker Attribution for Each Line
- For EACH line:
-- if the line is a quote:
--- print the line number : followed by n where n is the key for the appropriate character that speaks the quote.

Important Rules:
- Quote lines are lines that START and END with double quotes.
- Focus on narrative context to determine who is speaking
- Use surrounding text, character mentions, and narrative flow for attribution
- Focus on the dialog itself. Speakers will not refer to themselves.
- Make sure the conversations make sense for sequential text.

5. Example Output Format:
- char_map : {1: "narrator", 2:"Name", 3:"OtherName"}
- 2:2
- 4:3
- 10:2
- 11:2

Process:
- First identify ALL characters and create char_map
- Print the char_map in JSON format
- Scan for quoted lines
- For each quoted line, determine speaker based on context
- Output line number : speaker number

IMPORTANT:
- TAKE YOUR TIME AND PROCESS ALL QUOTED LINES INDIVIDUALLY.
- Report every line with a quote. There will be many times where thinking will have a range of lines. We need to process each quoted line and print the speaker for each line.
"""
#- Do NOT base attribution solely on the quote content itself
#- Print with final format in mind.
#- Do not stop until the full text is processed!
#- Do not summarize, go thought the entire text!
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Label a chapter file by character. Speaker (Narrator) for non quoted lines. Speaker (char_name) for spoken lines.")
    parser.add_argument("-txt_file", help="Path to the EPUB file")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose printing for debug.")
    parser.add_argument("--skip_llm", action="store_true", help="Skip call to LLM and just try to process files into character maps.")
    parser.add_argument("-num_llm_attempts", type=int, default=5, help="Number of llm attempts submitted.")
    args = parser.parse_args()
    client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio") # api_key can be any string as it's not used by LM Studio
    
    if not os.path.exists(args.txt_file):
        print("Invalid txt_file. Please specify a valid text file and retry.", file=sys.stderr)
        exit()

    chapter_file_base, _ = os.path.splitext(args.txt_file)

    if not args.skip_llm:
        with open(args.txt_file,"r",  encoding='utf-8') as f:
            lines = f.readlines()
        # Define your chat messages
        messages = [
            {"role": "system", "content": "You are a helpful assistant."+PROMPT_TXT}]
        [messages.append({"role": "user", "content": x}) for x in lines]

        for a, attempt in enumerate(range(args.num_llm_attempts)):
            # Send the chat completion request
            try:
                print(f"Processing attempt {a}")
                response = client.chat.completions.create(
                    model="local-model",  # Use a placeholder model name or the specific model ID from LM Studio
                    messages=messages,
                    temperature=0.7,
                    #stream=True # Set to True for streaming responses
                ).choices[0].message
                if "</think>" in response.content:
                    thought_process, result = response.content.split("</think>")
                else:
                    result = response.content
                    thought_process = response.reasoning
                # Save think files
                with open(chapter_file_base+f".think.{a}.txt", "w", encoding='utf-8') as f:
                    f.write(thought_process)
                # Save result files
                with open(chapter_file_base+f".result.{a}.txt", "w", encoding='utf-8') as f:
                    f.write(result)
            except Exception as e:
                print(f"An error occurred: {e}", file=sys.stderr)
    
    character_maps = []
    line_maps = []
    merged_character_map = {}
    for a, attempt in enumerate(range(args.num_llm_attempts)):
        with open(chapter_file_base+f".result.{a}.txt", "r", encoding='utf-8') as f:
            result = f.readlines()
        try:
            character_map, line_map = interpret_result(result, a)
        except Exception as e:
            print(f"Error in {chapter_file_base}.result.{a}.txt")
            raise e
        # print(a)
        # print(character_map)
        used_characters = set(line_map.values())
        # print("used_characters", character_map)
        if len(merged_character_map)==0:
            merged_character_map = character_map.copy()
            # Audit for character that is actually used.
            for key, character in character_map.items():
                if key not in used_characters and character != "narrator":
                    print(f"Removing un-used character in first map:")
                    print(key)
                    print(f"[{key}]{character}")
                    del merged_character_map[key]
        else:
            key_remap = {}
            for key, character in character_map.items():
                existing_character=False
                for m_key, m_character in merged_character_map.items():
                    if (character == m_character) or \
                       (character in m_character) or \
                       (m_character in character):
                        existing_character=True
                        key_remap[key] = m_key
                        if key == m_key:
                            print(f"Already matched character with same key: [{key}] {character}") 
                        else:
                            print(f"Matched character with different key: [{key}->{m_key}] {character}")
                if not existing_character:
                    character_is_used = character in line_map.values()
                    if character_is_used:
                        new_m_key = max(merged_character_map.keys())+1
                        merged_character_map[new_m_key] = character
                        key_remap[new_m_key]=new_m_key
                        print(f"New character with new key: [{new_m_key}]{character}")
                        # TODO: remap speakers to the new character
                    else:
                        print(f"Unused character {character}, will not be added.")
            # use key_remap on line_map
            print(key_remap)
            # print("PRE linemap")
            # print(line_map)
            line_map = {k:key_remap[v] for k,v in line_map.items() if v in key_remap.keys()}
            # print("POST linemap")
            # print(line_map)
        line_maps.append(line_map)
    # quit() # just merging together the maps for now, don't overwrite maps.
    if args.verbose:
        print(merged_character_map)
        print("line_maps:", len(line_maps))
    merged_line_map = merge_line_maps(line_maps, args.verbose)
    merged_line_map = dict(sorted(merged_line_map.items(), key=lambda x: int(x[0])))
    if args.verbose:
        print("Overall line map:")
        print(merged_line_map)
    with open(chapter_file_base+f".map.json", "w", encoding='utf-8') as f:
        f.write(json.dumps([merged_character_map, merged_line_map], indent=4))
    exit()