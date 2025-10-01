#!/usr/bin/env python3
"""
Simple Python script to parse an EPUB file into an array of chapters.
"""

import argparse
import sys
import os
from parse_chapter import valid_context_list, invalid_speaker_list
from parse_chapter import same_speaker_tokens, parse_epub_to_chapters

# Text to speach generation
import torch
from vibevoice.processor.vibevoice_processor import VibeVoiceProcessor
from vibevoice.modular.modeling_vibevoice_inference import VibeVoiceForConditionalGenerationInference
from demo.inference_from_file import VoiceMapper

# Voice to Text for validation
from difflib import SequenceMatcher
from faster_whisper import WhisperModel

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
    os.makedirs("./chapters", exist_ok=True)
    voice_mapper = VoiceMapper()

    target_device="cuda"
    model_path="Jmica/VibeVoice7B"#"microsoft/VibeVoice-1.5B"
    tts_model = VibeVoiceForConditionalGenerationInference.from_pretrained(
        model_path, # model_path 
        torch_dtype=torch.bfloat16,
        device_map=target_device,
        attn_implementation="flash_attention_2",
    )
    tts_model.eval()
    tts_model.set_ddpm_inference_steps(num_steps=10)
    processor = VibeVoiceProcessor.from_pretrained(model_path)

    if hasattr(tts_model.model, 'language_model'):
       print(f"Language model attention: {tts_model.model.language_model.config._attn_implementation}")

    validation_model = WhisperModel("tiny.en")
    for i, chapter in enumerate(chapters):
        #print(f"\n--- Chapter {i+1} ---")
        if args.by_chapter:
            for j, chapter_obj in enumerate(chapter):
                full_script=str(chapter_obj)
                ratio = 0.0
                max_ratio = 0.0
                retries = 0
                while ratio < 0.82 and retries < 10:
                    # Prepare inputs for the model
                    inputs = processor(
                        text=[full_script], # Wrap in list for batch processing
                        voice_samples=[voice_mapper.get_voice_path(speaker_name) for speaker_name in 
                                    ["en-John_man","en-Jeff_man","en-Alice_woman","en-Travis_man"]], # Wrap in list for batch processing
                        padding=True,
                        return_tensors="pt",
                        return_attention_mask=True,
                    )
                    for k, v in inputs.items():
                        if torch.is_tensor(v):
                            inputs[k] = v.to(target_device)

                    outputs = tts_model.generate(
                        **inputs,
                        max_new_tokens=None,
                        cfg_scale=1.4,#cfg_scale
                        tokenizer=processor.tokenizer,
                        generation_config={'do_sample': False},
                        verbose=False,
                    )

                    # Save output (processor handles device internally)
                    output_path = f"./chapters/chapter_{str(i).zfill(2)}.{str(j).zfill(4)}.tmp.wav"            
                    processor.save_audio(
                        outputs.speech_outputs[0], # First (and only) batch item
                        output_path=output_path,
                    )
                    #print(f"Saved output to {output_path}")
                    segments, info = validation_model.transcribe(f"./chapters/chapter_{str(i).zfill(2)}.{str(j).zfill(4)}.tmp.wav")
                    input_string = chapter_obj.text
                    detected_string = "\n".join([str(x.text) for x in segments])

                    ratio = SequenceMatcher(None, input_string.lower(), detected_string.lower()).ratio()
                    if ratio > max_ratio:
                        max_ratio = ratio
                        if os.path.exists( f"./chapters/chapter_{str(i).zfill(2)}.{str(j).zfill(4)}.wav"):
                            os.unlink(f"./chapters/chapter_{str(i).zfill(2)}.{str(j).zfill(4)}.wav")
                        os.rename(f"./chapters/chapter_{str(i).zfill(2)}.{str(j).zfill(4)}.tmp.wav",
                                   f"./chapters/chapter_{str(i).zfill(2)}.{str(j).zfill(4)}.wav")
                    print(str(j).zfill(4),", Attempt: ", retries+1, ", Ratio: ", ratio)
                    retries+=1
                if os.path.exists(f"./chapters/chapter_{str(i).zfill(2)}.{str(j).zfill(4)}.tmp.wav"):
                    os.unlink(f"./chapters/chapter_{str(i).zfill(2)}.{str(j).zfill(4)}.tmp.wav")
            break # chapters
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
