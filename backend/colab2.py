import os
import json
import requests
import whisper
import torch

# === Configs ===
VOICE_IDS = {
    "quiz": "fMpuMtuBbLqzac6r00Am",
    "bruce": "OfaedTFdEgJsFwZK1BiV",
    "wayne": "VYKg4tM6Oy6LclM5LvKO",
    "myra": "8qBGIaLTJL2SAnhbJlK3",
    "adam": "pNInz6obpgDQGcFmaJgB"
}
API_KEY_11_LABS = "008647ae5d21e87656507bb6ef123b34"

device = "cuda" if torch.cuda.is_available() else "cpu"
WHISPER_MODEL = whisper.load_model("large", device=device)

# === Image Processing ===

def upscale_image(image_path: str, output_dir: str) -> None:
    """Upscale a single image using Real‑ESRGAN."""
    command = (
        f'python ../Real-ESRGAN/inference_realesrgan.py'
        f' -n RealESRGAN_x4plus'
        f' -i "{image_path}"'
        f' -o "{output_dir}"'
    )
    status = os.system(command)
    if status == 0:
        print(f'[UPSCALE] {image_path} -> {output_dir}')
    else:
        print(f'[ERROR] Upscaling failed for {image_path}')

def process_images(quiz_dir: str) -> None:
    """Upscale every *.png in *quiz_dir* once, putting results into *quiz_dir/upscaled_images*."""
    upscaled_dir = os.path.join(quiz_dir, "upscaled_images")
    os.makedirs(upscaled_dir, exist_ok=True)

    for image in sorted(f for f in os.listdir(quiz_dir) if f.endswith(".png")):
        image_path = os.path.join(quiz_dir, image)
        upscale_image(image_path, upscaled_dir)

# === Audio Processing ===

def create_script(json_path: str) -> str:
    """Return the dialogue lines in the JSON as a newline‑separated script."""
    data = json.load(open(json_path))
    lines = data.get("lines", data)          # support both {"lines": [...]} and bare list
    return "\n".join(f'"{line[0]}"' for line in lines if isinstance(line, list) and line)

def convert_text_to_speech(text: str, voice_id: str, output_path: str) -> None:
    url = f'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?optimize_streaming_latency=0'
    headers = {
        'accept': 'audio/mpeg',
        'xi-api-key': API_KEY_11_LABS,
        'Content-Type': 'application/json'
    }
    payload = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
            "stability": 0,
            "similarity_boost": 0,
            "style": 0,
            "use_speaker_boost": True
        }
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=120)
    if resp.status_code == 200:
        with open(output_path, "wb") as f:
            f.write(resp.content)
        print(f'[AUDIO] saved to {output_path}')
    else:
        raise RuntimeError(f'TTS failed {resp.status_code}: {resp.text}')

def generate_audio_files(quiz_dir: str, voice_name: str = "adam") -> None:
    """Generate <voice_name>.mp3 for a quiz directory if it does not yet exist."""
    json_file = next((f for f in os.listdir(quiz_dir) if f.endswith(".json")), None)
    if not json_file:
        print(f'[SKIP] No script JSON found in {quiz_dir}')
        return

    audio_path = os.path.join(quiz_dir, f"{voice_name}.mp3")
    if os.path.exists(audio_path):
        print(f'[AUDIO] already exists: {audio_path}')
        return

    script = create_script(os.path.join(quiz_dir, json_file))
    convert_text_to_speech(script, VOICE_IDS[voice_name], audio_path)

# === Subtitle Processing ===

def extract_word_timings(audio_path: str) -> list[dict]:
    """Return a list of dicts with word‑level timings from Whisper."""
    result = WHISPER_MODEL.transcribe(audio_path, language="en", word_timestamps=True)

    words = []
    for segment in result.get("segments", []):
        for w in segment.get("words", []):
            if all(k in w for k in ("word", "start", "end")):
                words.append(
                    {
                        "text": w["word"],
                        "start": float(w["start"]),
                        "end": float(w["end"]),
                        "confidence": float(w.get("probability", 1.0)),
                    }
                )
    return words

def generate_subtitles(audio_path: str, subtitle_path: str, interactive: bool = False) -> list[dict]:
    words = extract_word_timings(audio_path)

    if interactive:
        # Optional manual correction
        for idx, w in enumerate(words):
            print(idx, w)
        user_in = input(
            "Enter corrections as 'index:new_word' separated by commas, or press Enter to accept all:\n"
        ).strip()
        for token in filter(bool, user_in.split(",")):
            idx, replacement = token.split(":")
            words[int(idx)]["text"] = replacement.strip()

    with open(subtitle_path, "w") as f:
        json.dump(words, f, indent=2)

    print(f'[SUB] subtitles written to {subtitle_path}')
    return words

# === SRT Creation ===

def _ts(t: float) -> str:
    sec = int(t)
    msec = int((t - sec) * 1000)
    return f"00:00:{sec:02d},{msec:03d}"

def create_srt(subtitles: list[dict], srt_path: str) -> None:
    with open(srt_path, "w") as f:
        for idx, sub in enumerate(subtitles, 1):
            f.write(f"{idx}\n")
            f.write(f"{_ts(sub['start'])} --> {_ts(sub['end'])}\n")
            f.write(f"{sub['text']}\n\n")
    print(f'[SRT] saved to {srt_path}')

def maybe_create_srt(quiz_dir: str) -> None:
    subtitle_path = os.path.join(quiz_dir, "subtitles.json")
    srt_path = os.path.join(quiz_dir, "subtitles.srt")
    if not os.path.exists(subtitle_path):
        print(f'[SKIP] {subtitle_path} not found')
        return
    if os.path.exists(srt_path):
        print(f'[SRT] already exists: {srt_path}')
        return

    subtitles = json.load(open(subtitle_path))
    create_srt(subtitles, srt_path)

# === Runner ===

def run_pipeline(base_path: str, interactive: bool = False) -> None:
    for quiz in os.listdir(base_path):
        quiz_dir = os.path.join(base_path, quiz)
        if not os.path.isdir(quiz_dir):
            continue

        print(f'=== Processing quiz "{quiz}" ===')
        process_images(quiz_dir)
        generate_audio_files(quiz_dir)
        subtitle_path = os.path.join(quiz_dir, "subtitles.json")
        audio_path = next(
            (os.path.join(quiz_dir, f) for f in os.listdir(quiz_dir) if f.endswith(".mp3")),
            None,
        )
        if audio_path and not os.path.exists(subtitle_path):
            generate_subtitles(audio_path, subtitle_path, interactive=interactive)

        maybe_create_srt(quiz_dir)

    # Clean up GPU memory
    torch.cuda.empty_cache()

# === Main ===
if __name__ == "__main__":
    BASE_PATH = "./mindset_story"   # <- put your quizzes here
    run_pipeline(BASE_PATH, interactive=False)
