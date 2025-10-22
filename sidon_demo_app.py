import gradio as gr
import numpy as np
import torch
import torchaudio
import transformers
import spaces
from huggingface_hub import hf_hub_download

fe_path = hf_hub_download("sarulab-speech/sidon-v0.1", filename="feature_extractor_cuda.pt")
decoder_path = hf_hub_download("sarulab-speech/sidon-v0.1", filename="decoder_cuda.pt")
preprocessor =  transformers.SeamlessM4TFeatureExtractor.from_pretrained(
    "facebook/w2v-bert-2.0",
    sampling_rate=16_000,
)
fe = torch.jit.load(fe_path,map_location='cuda').to('cuda')
decoder = torch.jit.load(decoder_path,map_location='cuda').to('cuda')

@spaces.GPU
def denoise_speech(audio):

    if audio is None:
        return None

    sample_rate, waveform = audio
    waveform = 0.9 * (waveform / np.abs(waveform).max())
    target_n_samples = int(48_000/sample_rate* waveform.shape[0])
    # Ensure waveform is a tensor
    if not isinstance(waveform, torch.Tensor):
        waveform = torch.tensor(waveform, dtype=torch.float32)

    # If stereo, convert to mono
    if waveform.ndim > 1 and waveform.shape[0] > 1:
        waveform = torch.mean(waveform, dim=1)

    # Add a batch dimension
    waveform = waveform.view(1, -1)
    wav = torchaudio.functional.highpass_biquad(waveform, sample_rate, 50)
    wav_16k = torchaudio.functional.resample(wav, sample_rate, 16_000)
    restoreds = []
    feature_cache = None
    wav_16k = torch.nn.functional.pad(wav_16k,(0,24000))
    for chunk in wav_16k.view(-1).split(16000 * 60):
        inputs = preprocessor(
            torch.nn.functional.pad(chunk, (40, 40)),
            return_tensors="pt",
            sampling_rate=16_000
        ).to('cuda')
        with torch.inference_mode():
            feature = fe(inputs["input_features"].to("cuda"))["last_hidden_state"]
            if feature_cache is not None:
                feature = torch.cat([feature_cache, feature], dim=1)
                restored_wav = decoder(feature.transpose(1, 2))
                restored_wav = restored_wav[:, :, 4800:]
            else:
                restored_wav = decoder(feature.transpose(1, 2))
                restored_wav = restored_wav[:, :, 50 * 3 :]
            feature_cache = feature[:, -5:, :]
        restoreds.append(restored_wav.cpu())
    restored_wav = torch.cat(restoreds, dim=-1)
    return 48_000, (restored_wav.view(-1, 1).numpy() * 32767).astype(np.int16)[:target_n_samples]


# Create the Gradio interface
iface = gr.Interface(
    fn=denoise_speech,
    inputs=gr.Audio(type="numpy", label="Noisy Speech"),
    outputs=gr.Audio(type="numpy", label="Restored Speech"),
    title="Sidon Speech Restoration",
    description="Upload a noisy audio file and the Sidon will restore it.",
)

if __name__ == "__main__":
    iface.launch()