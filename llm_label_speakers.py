#!/usr/bin/env python3
"""
Module to take a chapter and automate sending through LLM for labeling characters.
"""
import argparse
from openai import OpenAI
# from unsloth import FastLanguageModel
# from transformers import AutoModelForCausalLM, AutoTokenizer
# import torch

# MODEL_PATH = "D:/models/unsloth/GLM-4.5-Air-GGUF"#"D:/models/lmstudio-community/gpt-oss-20b-GGUF"
# MODEL_GGUF = "GLM-4.5-Air-Q4_K_S-00001-of-00002.gguf"#"gpt-oss-20b-MXFP4.gguf"
#""
#"D:/models/unsloth/GLM-4.5-Air-GGUF"#/#"unsloth/glm-4.5-air-q4"#"unsloth/GLM-4.5-Air-GGUF"#"zai-org/GLM-4.5"
# /opt/model-storage/GLM-4.5-Air-UD-Q4_K_XL-00001-of-00002.gguf
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
- For EACH line number:
-- If the line is not a quote, add a prefix of "Speaker 1". This indicates the speaker is the narrator, our first character.
-- If the line is a quote, add the prefix of "Speaker n" where n is the key for the appropriate character that speaks the quote.

Important Rules:
- Quote lines are lines that START and END with double quotes.
- Focus on narrative context to determine who is speaking
- Do NOT base attribution solely on the quote content itself
- Use surrounding text, character mentions, and narrative flow for attribution
- Focus on the dialog itself as well. Speakers will not refer to themselves. 
- Make sure the conversations make sense for sequential text. 

5. Example Output Format:
- char_map : {1: "narrator", 2:"Name"}
- Speaker 1: This is a narrator line as it does not start and end with double quotes. The next line is spoken by the character Name.
- Speaker 2 "This is a the text spoken by Name"

Process:
- First identify ALL characters and create char_map
- Print the char_map in JSON format
- Scan for quoted lines
- For each quoted line, determine speaker based on context
- Output all lines in specified format

IMPORTANT:
- TAKE YOUR TIME AND PRINT ALL LINES! 
- Print with final format in mind.
- We have plenty of memory and context!
- JUST ADD PREFIX BUT DONT ALTER THE ACTUAL TEXT OF THE LINES THEMSELVES! 
- Do not stop until the full text is fully printed!
- Do not summarize, go thought the entire text!
- Do not say when the task is complete, just stop printing lines.
"""
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Label a chapter file by character. Speaker (Narrator) for non quoted lines. Speaker (char_name) for spoken lines.")
    parser.add_argument("-txt_file", help="Path to the EPUB file")
    args = parser.parse_args()
    client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio") # api_key can be any string as it's not used by LM Studio


    with open(args.txt_file,"r") as f:
        lines = f.readlines()
    # Define your chat messages
    messages = [
        {"role": "system", "content": "You are a helpful assistant."+PROMPT_TXT}]
    [messages.append({"role": "user", "content": x}) for x in lines]

    # Send the chat completion request
    try:
        completion = client.chat.completions.create(
            model="local-model",  # Use a placeholder model name or the specific model ID from LM Studio
            messages=messages,
            temperature=0.7,
            stream=True # Set to True for streaming responses
        )
        # Process the response (for streaming)
        for chunk in completion:
            if chunk.choices[0].delta.content:
                print(chunk.choices[0].delta.content, end="")
    except Exception as e:
        print(f"An error occurred: {e}")
    # model, tokenizer = FastLanguageModel.from_pretrained("unsloth/glm-4.5-air-q4")#, load_in_4bit=True
    # tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH,gguf_file=MODEL_GGUF)
    # model = AutoModelForCausalLM.from_pretrained(
    #     MODEL_PATH,
    #     gguf_file=MODEL_GGUF,
    #     local_files_only=True,
    #     # torch_dtype=torch.bfloat16,
    #     device_map="cuda:1"
    # )

    exit()