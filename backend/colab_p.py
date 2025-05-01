import os
import json
import requests
import whisper
import torch
import logging
import subprocess
# === Configs ===
VOICE_IDS = {
    "quiz": "fMpuMtuBbLqzac6r00Am",
    "bruce": "OfaedTFdEgJsFwZK1BiV",
    "wayne": "VYKg4tM6Oy6LclM5LvKO",
    "myra": "8qBGIaLTJL2SAnhbJlK3",
    "adam": "pNInz6obpgDQGcFmaJgB"
}
API_KEY_11_LABS = "008647ae5d21e87656507bb6ef123b34"

device1 = "cuda" if torch.cuda.is_available() else "cpu"
WHISPER_MODEL = whisper.load_model("large", device=device1)

# === Image Processing ===
def upscale_image(image_path, output_dir):
    try:
        command = f'python ../Real-ESRGAN/inference_realesrgan.py -n RealESRGAN_x4plus -i "{image_path}" -o "{output_dir}"'
        os.system(command)
        logging.info(f'Upscaled: {image_path} -> {output_dir}')
    except Exception as e:
        logging.info(f'Upscaling failed for {image_path}: {e}')

def process_images(base_path): 
    quiz_dir_path = os.path.join(base_path)
    logging.info(quiz_dir_path)
    upscaled_dir = os.path.join(quiz_dir_path, "upscaled_images")
    os.makedirs(upscaled_dir, exist_ok=True)

    images = [f for f in os.listdir(quiz_dir_path) if f.endswith(".png")]
    for image in images:
        image_path = os.path.join(quiz_dir_path, image)
        logging.info(f'Processing image: {image_path}')
        upscale_image(image_path, upscaled_dir)

# === Audio Processing ===
def create_script(json_path):
    data = json.load(open(json_path))
    lines = data.get("lines", [])  # Adjust this key based on actual JSON
    return "\n".join(f'"{line[0]}"' for line in lines if isinstance(line, list) and line)


    return "\n".join(f'"{line[0]}"' for line in data[:-1])

def convert_text_to_speech(text, voice_id, output_path):
    url = f'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?optimize_streaming_latency=0'
    headers = {
        'accept': 'audio/mpeg',
        'xi-api-key': API_KEY_11_LABS,
        'Content-Type': 'application/json'
    }
    data = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
            "stability": 0,
            "similarity_boost": 0,
            "style": 0,
            "use_speaker_boost": True
        }
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        with open(output_path, 'wb') as f:
            f.write(response.content)
        logging.info(f'Audio saved: {output_path}')
    else:
        logging.info(f'Failed to generate audio: {response.status_code} - {response.text}')

def generate_audio_files(base_path, voice_name="adam"):
    dir_path = os.path.join(base_path)
    json_file = next((f for f in os.listdir(dir_path) if f.endswith(".json")), None)
    logging.info(f"------------------------------------------------------generate_audio_files:")
    if json_file:
        script = create_script(os.path.join(dir_path, json_file))
        audio_path = os.path.join(dir_path, f"{voice_name}.mp3")
        logging.info(f"Audio path: {audio_path}-------------------------------------")
        if not os.path.exists(audio_path):

            logging.info(f"Audio file does not exist, generating: {audio_path}")
            convert_text_to_speech(script, VOICE_IDS[voice_name], audio_path)

# === Subtitle Processing ===
def extract_word_timings(audio_path):
    audio = whisper.load_audio(audio_path)
    result = whisper.transcribe(WHISPER_MODEL, audio, language="en", word_timestamps=True)
    
    words = []
    for segment in result.get("segments", []):
        segment_words = segment.get("words", [])
        logging.info([w.keys() for w in segment_words])

        for w in segment_words:
            if all(k in w for k in ("word", "start", "end")):
                words.append({
                    "text": w["word"],                     # renamed key
                    "start": float(w["start"]),
                    "end": float(w["end"]),
                    "confidence": float(w.get("probability", 1.0))  # mapped + fallback
                })
            else:
                logging.info(f"Skipping malformed word entry: {w}")
    
    return words




# def optionally_correct_subtitles(words):
#     for idx, word in enumerate(words):
#         print(idx, word)
#     # inp = input("Enter corrections in format 'index:new_word' (comma separated), or press Enter to skip:\n")
#     # if not inp.strip():
#     #     return words
#     for part in inp.split(','):
#         index, new_word = part.split(':')
#         words[int(index)]["text"] = new_word.strip()
#     return words

# def generate_subtitles(audio_path, save_path):
#     words = extract_word_timings(audio_path)
#     # words = optionally_correct_subtitles(words)
#     with open(save_path, 'w') as f:
#         json.dump(words, f)
#     return words

# def generate_all_subtitles(base_path):
    
#     dir_path = os.path.join(base_path)
#     audio_file = next((f for f in os.listdir(dir_path) if f.endswith(".mp3")), None)
#     if audio_file:
#         audio_path = os.path.join(dir_path, audio_file)
#         subtitle_path = os.path.join(dir_path, "subtitles", "subtitles.json")
#         if not os.path.exists(subtitle_path):
#             generate_subtitles(audio_path, subtitle_path)

#     del model
#     torch.cuda.empty_cache()



def get_words_and_time(model, speech):
  audio = whisper.load_audio(speech)
  result = whisper.transcribe(model, audio, language="en")
  result_timestamped = json.loads(json.dumps(result, indent = 2, ensure_ascii = False))
  words = []
  for i in range(len(result_timestamped['segments'])):
    words += result_timestamped['segments'][i]['words']
  array = [{'text':i['text'],'start':i['start'], 'end':i['end'],'confidence':i['confidence']} for i in words]
  return array

def correct_subtitles(text_timestamped):
  len_out = len(text_timestamped)
  for i in range(len_out):
    logging.info(i, text_timestamped[i])
  ip = input()
  if ip.strip() == '':
    return text_timestamped
  else:
    to_change = [(int(i.split(':')[0].strip()), i.split(':')[1].strip()) for i in ip.split(',')]
    for ind, new_word in to_change:
      logging.info('ind', ind, 'new_word', new_word)
      new_word_dict = {}
      new_word_dict[new_word] = list(text_timestamped[ind].values())[0]
      text_timestamped[ind] = new_word_dict
    logging.info('text_timestamped', text_timestamped)
    return text_timestamped

def make_text_timestamped(audio_path, save_path):
  text_timestamped = get_words_and_time(WHISPER_MODEL, audio_path)
  text_timestamped = correct_subtitles(text_timestamped)
  json.dump(text_timestamped, open(save_path, 'w'))
  return text_timestamped

def generate_all_subtitles(base_path):
#   quiz_dirs = os.listdir(base_path)
  dir_path = os.path.join(base_path)
  audio_file = next((f for f in os.listdir(dir_path) if f.endswith(".mp3")), None)
  if audio_file:
    audio_path = os.path.join(dir_path, audio_file)
    subtitles_path = os.path.join(base_path, "subtitles.json")
    if not os.path.exists(subtitles_path):
        text_timestamped = make_text_timestamped(audio_path, subtitles_path)


# === SRT Creation ===
def format_timestamp(t):
    sec = int(t)
    msec = int((t - sec) * 1000)
    return f"00:00:{sec:02d},{msec:03d}"

def create_srt_from_subtitles(subtitles, output_path):
    with open(output_path, 'w') as f:
        for idx, sub in enumerate(subtitles, 1):
            f.write(f"{idx}\n")
            f.write(f"{format_timestamp(sub['start'])} --> {format_timestamp(sub['end'])}\n")
            f.write(f"{sub['text']}\n\n")

def generate_srt_files(base_path):
    for quiz_dir in os.listdir(base_path):
        dir_path = os.path.join(base_path, quiz_dir)
        #os.makedirs(dir_path, exist_ok=True)
        subtitle_path = os.path.join(dir_path, "subtitles.json")
        srt_path = os.path.join(dir_path, "subtitles.srt")
        if os.path.exists(subtitle_path) and not os.path.exists(srt_path):
            subtitles = json.load(open(subtitle_path))
            create_srt_from_subtitles(subtitles, srt_path)


def create_video_from_images_with_audio(
    image_dir: str,
    audio_file: str,
    output_file: str = "output.mp4",
    framerate: int = 1,
    video_fps: int = 30
):
    """
    Creates a video from a sequence of images and an audio file using ffmpeg.

    Args:
        image_dir (str): Path to the directory containing sequential images (e.g., 0.png, 1.png, ...).
        audio_file (str): Path to the audio file to include in the video.
        output_file (str): Output video filename. Defaults to 'output.mp4'.
        framerate (int): How many seconds each image should be shown. Defaults to 1.
        video_fps (int): Output video framerate. Defaults to 30.
    """

    # Store current working directory to restore later
    original_dir = os.getcwd()
    os.chdir(image_dir)

    # FFmpeg command
    cmd = [
        "ffmpeg",
        "-y",                           # Overwrite output file if it exists
        "-framerate", str(framerate),  # Duration per image
        "-i", "%d.png",                # Input image sequence
        "-i", audio_file,              # Audio file
        "-c:v", "libx264",             # H.264 codec
        "-r", str(video_fps),          # Output framerate
        "-pix_fmt", "yuv420p",         # Compatibility format
        "-shortest",                   # Cut off at end of shortest input
        output_file
    ]

    # Run ffmpeg
    try:
        subprocess.run(cmd, check=True)
        logging.info(f"[✓] Video created successfully: {output_file}")
    except subprocess.CalledProcessError as e:
        logging.info("[✗] Error during video creation:", e)
    finally:
        os.chdir(original_dir)



# === Runner ===
def run_pipeline(base_path):
    logging.info("Upscaling images...")
    process_images(base_path)

    logging.info("Generating audio...")
    generate_audio_files(base_path)

    logging.info("Creating subtitles...")
    generate_all_subtitles(base_path)

    logging.info("Exporting SRT files...")
    generate_srt_files(base_path)

    create_video_from_images_with_audio( image_dir=f"{base_path}/upscaled_images/", audio_file=f"{base_path}/adam.mp3",output_file=f"{base_path}/story_video.mp4")

# === Main ===
if __name__ == "__main__":
    base_path = "./mindset_story"  # Update this with your actual path
    run_pipeline(base_path)
