#!/usr/bin/env python3
"""
Simple Python script to parse an EPUB file into an array of chapters.
"""

import argparse
import sys
import os
import time

from parse_chapter import valid_context_list, invalid_speaker_list, speaker_map
from parse_chapter import same_speaker_tokens, parse_epub_to_chapters

# Text to speach generation
import torch
from vibevoice.processor.vibevoice_processor import VibeVoiceProcessor
from vibevoice.modular.modeling_vibevoice_inference import VibeVoiceForConditionalGenerationInference
from demo.inference_from_file import VoiceMapper

# Voice to Text for validation
from difflib import SequenceMatcher
from faster_whisper import WhisperModel

# combine auido files
import glob
import pydub

# Filter audio files
from sidon_demo_app import denoise_speech
import torchaudio
import gradio as gr
from scipy.io import wavfile
# import numpy as np
# import torchaudio
# import transformers
# import spaces
# from huggingface_hub import hf_hub_download

# fe_path = hf_hub_download("sarulab-speech/sidon-v0.1", filename="feature_extractor_cuda.pt")
# decoder_path = hf_hub_download("sarulab-speech/sidon-v0.1", filename="decoder_cuda.pt")
# preprocessor =  transformers.SeamlessM4TFeatureExtractor.from_pretrained(
#     "facebook/w2v-bert-2.0",
# )

# @spaces.GPU
# def denoise_speech(audio, fe, decoder):
#     if audio is None:
#         return None

#     waveform, sample_rate = audio
#     #print("sample_rate",sample_rate)
#     #print("waveform",waveform)
#     waveform = 0.9 * (waveform / np.abs(waveform).max())
#     target_n_samples = int(48_000/sample_rate* waveform.shape[0])
#     # Ensure waveform is a tensor
#     if not isinstance(waveform, torch.Tensor):
#         waveform = torch.tensor(waveform, dtype=torch.float32)

#     # If stereo, convert to mono
#     if waveform.ndim > 1 and waveform.shape[0] > 1:
#         waveform = torch.mean(waveform, dim=1)

#     # Add a batch dimension
#     waveform = waveform.view(1, -1)
#     wav = torchaudio.functional.highpass_biquad(waveform, sample_rate, 50)
#     wav_16k = torchaudio.functional.resample(wav, sample_rate, 16_000)
#     restoreds = []
#     feature_cache = None
#     wav_16k = torch.nn.functional.pad(wav_16k,(0,24000))
#     for chunk in wav_16k.view(-1).split(16000 * 60):
#         inputs = preprocessor(
#             torch.nn.functional.pad(chunk, (40, 40)), return_tensors="pt",
#         ).to('cuda')
#         with torch.inference_mode():
#             feature = fe(inputs["input_features"].to("cuda"))["last_hidden_state"]
#             if feature_cache is not None:
#                 feature = torch.cat([feature_cache, feature], dim=1)
#                 restored_wav = decoder(feature.transpose(1, 2))
#                 restored_wav = restored_wav[:, :, 4800:]
#             else:
#                 restored_wav = decoder(feature.transpose(1, 2))
#                 restored_wav = restored_wav[:, :, 50 * 3 :]
#             feature_cache = feature[:, -5:, :]
#         restoreds.append(restored_wav.cpu())
#     restored_wav = torch.cat(restoreds, dim=-1)
#     return 48_000, (restored_wav.view(-1, 1).numpy() * 32767).astype(np.int16)[:target_n_samples]

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
    voices_map = {
        1: "en-Travis_man",
        2: "en-John_man",
        3: "en-Rosumand_woman",
        4: "en-Frank_man",#"en-Alice_woman"
    }
    validation_model = WhisperModel("tiny.en")
    for i, chapter in enumerate(chapters):
        if i==0:
            continue
        #print(f"\n--- Chapter {i+1} ---")
        if args.by_chapter:
            for voice_idx in reversed(voices_map.keys()):
                # Re-initialize the processor for a new voice
                tts_model = VibeVoiceForConditionalGenerationInference.from_pretrained(
                    model_path, # model_path 
                    torch_dtype=torch.bfloat16,
                    device_map=target_device,
                    attn_implementation="flash_attention_2",
                )
                tts_model.eval()
                tts_model.set_ddpm_inference_steps(num_steps=10)
                processor = VibeVoiceProcessor.from_pretrained(model_path)
                for j, chapter_obj in enumerate(chapter):
                    if voice_idx != speaker_map[chapter_obj.get_speaker()]:
                        continue # skip if its a different voice
                    full_script="Speaker 1: "+str(chapter_obj.text)+str("        .\n")
                    ratio = 0.0
                    max_ratio = 0.0
                    retries = 0
                    while ratio < 0.9 and retries < 10:
                        # Prepare inputs for the model
                        voice_used = voices_map[voice_idx]
                        inputs = processor(
                            text=[full_script], # Wrap in list for batch processing
                            voice_samples=[voice_mapper.get_voice_path(voice_used)],
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

                        # send through a cleaning ML algo
                        sample_rate, waveform = wavfile.read(output_path)
                        sample_rate, waveform = denoise_speech((sample_rate,waveform))
                        wavfile.write(output_path, sample_rate, waveform)

                        # remove long silences after filtering

                        #print(f"Saved output to {output_path}")
                        segments, info = validation_model.transcribe(f"./chapters/chapter_{str(i).zfill(2)}.{str(j).zfill(4)}.tmp.wav")
                        input_string = chapter_obj.text
                        detected_string = "\n".join([str(x.text) for x in segments])

                        ratio = SequenceMatcher(None, input_string.lower(), detected_string.lower()).quick_ratio() # quick ratio doesn't care about oder just set match
                        if ratio > max_ratio:
                            max_ratio = ratio
                            if os.path.exists( f"./chapters/chapter_{str(i).zfill(2)}.{str(j).zfill(4)}.wav"):
                                os.unlink(f"./chapters/chapter_{str(i).zfill(2)}.{str(j).zfill(4)}.wav")
                            time.sleep(2) # make sure the file is closed by the time we rename it
                            os.rename(f"./chapters/chapter_{str(i).zfill(2)}.{str(j).zfill(4)}.tmp.wav",
                                    f"./chapters/chapter_{str(i).zfill(2)}.{str(j).zfill(4)}.wav")
                        print(str(j).zfill(4),", Attempt: ", retries+1, ", Ratio: ", int(ratio*100), "Voice: ", voice_used, full_script[:50])
                        # input_ids', 'attention_mask', 'speech_input_mask', 'speech_tensors', 'speech_masks', 'parsed_scripts', 'all_speakers_list'
                        retries+=1
                    if os.path.exists(f"./chapters/chapter_{str(i).zfill(2)}.{str(j).zfill(4)}.tmp.wav"):
                        os.unlink(f"./chapters/chapter_{str(i).zfill(2)}.{str(j).zfill(4)}.tmp.wav")
            wavs = glob.glob(f"./chapters/chapter_*.*.wav")
            combo = None
            for wav in wavs:
                if combo is None:
                    combo = pydub.AudioSegment.from_wav(wav)
                else:
                    combo = combo+pydub.AudioSegment.from_wav(wav)
            combo.export(f"./chapters/chapter_{str(i).zfill(2)}.mp3", format="mp3")
            # remove the wav files
            [os.unlink(x) for x in wavs]
            # break # chapters
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
