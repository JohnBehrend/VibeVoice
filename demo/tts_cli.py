#!C:\Users\j3p3\Documents\Repos\VibeVoice\.venv\Scripts\python.exe python3
"""
Command Line Interface for VibeVoice Text-to-Speech
"""

import argparse
import os
import sys
import torch
import librosa
import numpy as np
import soundfile as sf
from pathlib import Path

# Add the project root to the path so we can import vibevoice modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vibevoice.modular.configuration_vibevoice import VibeVoiceConfig
from vibevoice.modular.modeling_vibevoice_inference import VibeVoiceForConditionalGenerationInference
from vibevoice.processor.vibevoice_processor import VibeVoiceProcessor
from vibevoice.modular.streamer import AudioStreamer
from transformers.utils import logging
from transformers import set_seed

# Set logging to info level
logging.set_verbosity_info()
logger = logging.get_logger(__name__)

class VibeVoiceTTS:
    def __init__(self, model_path: str, inference_steps: int = 5):
        """Initialize the VibeVoice TTS with model loading."""
        self.model_path = model_path
        self.device = "cuda"
        self.inference_steps = inference_steps
        self.load_model()
        self.setup_voice_presets()
        
    def load_model(self):
        """Load the VibeVoice model and processor."""
        print(f"Loading processor & model from {self.model_path}")
        
        # Load processor
        self.processor = VibeVoiceProcessor.from_pretrained(self.model_path)
        
        # Decide dtype & attention for CUDA
        load_dtype = torch.bfloat16
        attn_impl_primary = "flash_attention_2"
            
        print(f"Using device: {self.device}, torch_dtype: {load_dtype}, attn_implementation: {attn_impl_primary}")
        
        # Load model for CUDA
        self.model = VibeVoiceForConditionalGenerationInference.from_pretrained(
                self.model_path,
                torch_dtype=load_dtype,
                device_map="cuda",
                attn_implementation=attn_impl_primary)
                
        self.model.eval()
        
        # Use SDE solver by default
        self.model.model.noise_scheduler = self.model.model.noise_scheduler.from_config(
            self.model.model.noise_scheduler.config, 
            algorithm_type='sde-dpmsolver++',
            beta_schedule='squaredcos_cap_v2'
        )
        self.model.set_ddpm_inference_steps(num_steps=self.inference_steps)
        
        if hasattr(self.model.model, 'language_model'):
            print(f"Language model attention: {self.model.model.language_model.config._attn_implementation}")
    
    def setup_voice_presets(self):
        """Setup voice presets by scanning the voices directory."""
        voices_dir = os.path.join(os.path.dirname(__file__), "voices")
        
        # Check if voices directory exists
        if not os.path.exists(voices_dir):
            print(f"Warning: Voices directory not found at {voices_dir}")
            self.voice_presets = {}
            self.available_voices = {}
            return
        
        # Scan for all WAV files in the voices directory
        self.voice_presets = {}
        
        # Get all .wav files in the voices directory
        wav_files = [f for f in os.listdir(voices_dir) 
                    if f.lower().endswith(('.wav', '.mp3', '.flac', '.ogg', '.m4a', '.aac')) and os.path.isfile(os.path.join(voices_dir, f))]
        
        # Create dictionary with filename (without extension) as key
        for wav_file in wav_files:
            # Remove .wav extension to get the name
            name = os.path.splitext(wav_file)[0]
            # Create full path
            full_path = os.path.join(voices_dir, wav_file)
            self.voice_presets[name] = full_path
        
        # Sort the voice presets alphabetically by name for better UI
        self.voice_presets = dict(sorted(self.voice_presets.items()))
        
        # Filter out voices that don't exist (this is now redundant but kept for safety)
        self.available_voices = {
            name: path for name, path in self.voice_presets.items()
            if os.path.exists(path)
        }
        
        if not self.available_voices:
            raise RuntimeError("No voice presets found. Please add .wav files to the demo/voices directory.")
        
        print(f"Found {len(self.available_voices)} voice files in {voices_dir}")
        print(f"Available voices: {', '.join(self.available_voices.keys())}")
    
    def read_audio(self, audio_path: str, target_sr: int = 24000) -> np.ndarray:
        """Read and preprocess audio file."""
        try:
            wav, sr = sf.read(audio_path)
            if len(wav.shape) > 1:
                wav = np.mean(wav, axis=1)
            if sr != target_sr:
                wav = librosa.resample(wav, orig_sr=sr, target_sr=target_sr)
            return wav
        except Exception as e:
            print(f"Error reading audio {audio_path}: {e}")
            return np.array([])
    
    def generate_audio(self, 
                      text: str,
                      voice_name: str = "en-Alice_woman",
                      cfg_scale: float = 1.3,
                      output_file: str = None) -> np.ndarray:
        """
        Generate audio from text using the specified voice.
        
        Args:
            text (str): Text to convert to speech
            voice_name (str): Name of the voice to use
            cfg_scale (float): CFG scale for generation
            output_file (str): Optional path to save the output audio file
            
        Returns:
            np.ndarray: Generated audio data
        """
        # Validate inputs
        if not text.strip():
            raise ValueError("Error: Please provide text to convert to speech.")
            
        if voice_name not in self.available_voices:
            raise ValueError(f"Error: Voice '{voice_name}' not found. Available voices: {list(self.available_voices.keys())}")
        
        # Load voice sample
        audio_path = self.available_voices[voice_name]
        audio_data = self.read_audio(audio_path)
        if len(audio_data) == 0:
            raise ValueError(f"Error: Failed to load audio for {voice_name}")
        
        # Prepare script - use speaker format
        formatted_script = f"Speaker 0: {text.strip()}"
        
        # Process inputs
        inputs = self.processor(
            text=[formatted_script],
            voice_samples=[[audio_data]],  # Single speaker with one voice sample
            padding=True,
            return_tensors="pt",
            return_attention_mask=True,
        )
        
        # Move tensors to device
        target_device = "cuda"
        for k, v in inputs.items():
            if torch.is_tensor(v):
                inputs[k] = v.to(target_device)
        
        # Create audio streamer
        audio_streamer = AudioStreamer(
            batch_size=1,
            stop_signal=None,
            timeout=None
        )
        
        # Generate audio
        def check_stop_generation():
            return False  # No stopping in CLI mode
            
        try:
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=None,
                cfg_scale=cfg_scale,
                tokenizer=self.processor.tokenizer,
                generation_config={
                    'do_sample': False,
                },
                audio_streamer=audio_streamer,
                stop_check_fn=check_stop_generation,
                verbose=False,
                refresh_negative=True,
            )
        except Exception as e:
            print(f"Error during generation: {e}")
            raise
        
        # Collect all audio chunks
        sample_rate = 24000
        audio_chunks = []
        
        # Get the stream for the first (and only) sample
        audio_stream = audio_streamer.get_stream(0)
        
        for audio_chunk in audio_stream:
            if torch.is_tensor(audio_chunk):
                # Convert bfloat16 to float32 first, then to numpy
                if audio_chunk.dtype == torch.bfloat16:
                    audio_chunk = audio_chunk.float()
                audio_np = audio_chunk.cpu().numpy().astype(np.float32)
            else:
                audio_np = np.array(audio_chunk, dtype=np.float32)
            
            # Ensure audio is 1D and properly normalized
            if len(audio_np.shape) > 1:
                audio_np = audio_np.squeeze()
                
            audio_chunks.append(audio_np)
        
        # Concatenate all chunks
        if audio_chunks:
            full_audio = np.concatenate(audio_chunks)
            
            # Save to file if output path provided
            if output_file:
                sf.write(output_file, full_audio, sample_rate)
                print(f"Audio saved to {output_file}")
                
            return full_audio
        else:
            raise RuntimeError("No audio was generated")

def parse_args():
    parser = argparse.ArgumentParser(description="VibeVoice Command Line TTS")
    parser.add_argument(
        "--model_path",
        type=str,
        default="Jmica/VibeVoice7B",
        help="Path to the VibeVoice model directory",
    )
    parser.add_argument(
        "--inference_steps",
        type=int,
        default=10,
        help="Number of inference steps for DDPM",
    )
    parser.add_argument(
        "--text",
        type=str,
        required=True,
        help="Text to convert to speech",
    )
    parser.add_argument(
        "--voice",
        type=str,
        default="en-Alice_woman",
        help="Voice name to use (default: en-Alice_woman)",
    )
    parser.add_argument(
        "--cfg_scale",
        type=float,
        default=1.3,
        help="CFG scale for generation (default: 1.3)",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output audio file path (.wav format)",
    )
    
    return parser.parse_args()

def main():
    """Main function to run the CLI TTS."""
    args = parse_args()
    
    set_seed(42)  # Set a fixed seed for reproducibility
    
    print("🎙️ Initializing VibeVoice TTS CLI...")
    
    try:
        # Initialize TTS instance
        tts = VibeVoiceTTS(
            model_path=args.model_path,
            inference_steps=args.inference_steps
        )
        
        print(f"📝 Converting text to speech with voice: {args.voice}")
        print(f"💬 Text: {args.text[:100]}{'...' if len(args.text) > 100 else ''}")
        
        # Generate audio
        audio_data = tts.generate_audio(
            text=args.text,
            voice_name=args.voice,
            cfg_scale=args.cfg_scale,
            output_file=args.output
        )
        
        print(f"✅ Audio generation completed successfully!")
        if args.output:
            print(f"📁 Audio saved to: {args.output}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
