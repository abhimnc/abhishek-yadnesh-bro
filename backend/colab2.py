import os
import json
import requests
import torch
import logging
import subprocess
import dotenv

dotenv.load_dotenv()

# === Logging Config ===
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# === Configs ===
VOICE_IDS = {
    "quiz": "aura-asteria-en",
    "bruce": "aura-hades-en",
    "wayne": "aura-titan-en",
    "myra": "aura-athena-en",
    "adam": "aura-zeus-en"
}

API_KEY_DEEPGRAM = os.getenv("DEEPGRAM_API_KEY")
if not API_KEY_DEEPGRAM:
    raise EnvironmentError("DEEPGRAM_API_KEY is not set")

DEEPGRAM_MAX_CHARS = 2000

# === Audio Processing ===
def create_script(json_path):
    try:
        logging.info(f"Loading story JSON: {json_path}")
        with open(json_path, "r") as f:
            data = json.load(f)
        return [ele.get("line", "") for ele in data.get("image_prompts", []) if ele.get("line")]
    except Exception as e:
        logging.error(f"Error creating script: {e}")
        return []

def convert_text_to_speech(text, voice_id, output_path):
    try:
        text = text.strip()
        if not text:
            logging.warning("Skipping empty TTS chunk")
            return False

        logging.info(f"TTS chunk length: {len(text)}")

        response = requests.post(
            "https://api.deepgram.com/v1/speak",
            headers={
                "Authorization": f"Token {API_KEY_DEEPGRAM}",
                "Content-Type": "application/json"
            },
            params={
                "encoding": "mp3",
                "model": voice_id
            },
            json={
                "text": text
            }
        )

        if response.status_code == 200:
            with open(output_path, "wb") as f:
                f.write(response.content)
            return True

        logging.error(f"TTS failed: {response.status_code} - {response.text}")
        return False

    except Exception as e:
        logging.error(f"TTS error: {e}")
        return False


def generate_audio_files(base_path, voice_name="adam", ffmpeg_path="ffmpeg"):
    try:
        # 🔍 Find any .json file in base_path
        json_files = [
            f for f in os.listdir(base_path)
            if f.lower().endswith(".json")
        ]

        if not json_files:
            logging.error("No .json file found in base_path")
            return

        json_path = os.path.join(base_path, json_files[0])
        logging.info(f"Using JSON file: {json_files[0]}")

        story_lines = create_script(json_path)
        if not story_lines:
            logging.error("No story lines found")
            return

        final_audio = os.path.join(base_path, f"{voice_name}.mp3")
        if os.path.exists(final_audio):
            logging.info("Final audio already exists, skipping TTS")
            return

        temp_files = []
        chunk = ""
        idx = 0

        for line in story_lines:
            if len(chunk) + len(line) <= DEEPGRAM_MAX_CHARS:
                chunk += line + " "
            else:
                temp_path = os.path.join(base_path, f"temp_{idx}.mp3")
                if convert_text_to_speech(chunk.strip(), VOICE_IDS[voice_name], temp_path):
                    temp_files.append(temp_path)
                    idx += 1
                chunk = line + " "

        if chunk.strip():
            temp_path = os.path.join(base_path, f"temp_{idx}.mp3")
            if convert_text_to_speech(chunk.strip(), VOICE_IDS[voice_name], temp_path):
                temp_files.append(temp_path)

        if not temp_files:
            logging.error("No audio chunks generated")
            return

        concat_list = os.path.join(base_path, "concat.txt")
        with open(concat_list, "w") as f:
            for p in temp_files:
                f.write(f"file '{os.path.basename(p)}'\n")

        cwd = os.getcwd()
        os.chdir(base_path)
        try:
            subprocess.run(
                [
                    ffmpeg_path,
                    "-y",
                    "-f", "concat",
                    "-safe", "0",
                    "-i", "concat.txt",
                    "-c", "copy",
                    os.path.basename(final_audio)
                ],
                check=True
            )
            logging.info(f"Final audio created: {final_audio}")
        finally:
            os.chdir(cwd)
            for p in temp_files:
                os.remove(p)
            os.remove(concat_list)

    except Exception as e:
        logging.error(f"Audio generation error: {e}")

# === Subtitle Processing ===
def extract_word_timings(audio_path):
    try:
        response = requests.post(
            "https://api.deepgram.com/v1/listen",
            headers={
                "Authorization": f"Token {API_KEY_DEEPGRAM}",
                "Content-Type": "audio/mp3"
            },
            params={
                "punctuate": "true",
                "model": "nova",
                "language": "en"
            },
            data=open(audio_path, "rb")
        )

        if response.status_code != 200:
            logging.error(f"ASR failed: {response.text}")
            return []

        words = []
        alt = response.json()["results"]["channels"][0]["alternatives"][0]
        for w in alt.get("words", []):
            words.append({
                "text": w["word"],
                "start": float(w["start"]),
                "end": float(w["end"])
            })
        return words
    except Exception as e:
        logging.error(f"Word timing error: {e}")
        return []

def generate_subtitles(base_path, voice_name="adam"):
    audio_path = os.path.join(base_path, f"{voice_name}.mp3")
    if not os.path.exists(audio_path):
        logging.error("Audio file not found for subtitles")
        return

    sub_json = os.path.join(base_path, "subtitles.json")
    if os.path.exists(sub_json):
        logging.info("Subtitles already exist")
        return

    words = extract_word_timings(audio_path)
    with open(sub_json, "w") as f:
        json.dump(words, f, indent=2)

# === SRT Creation ===
def format_timestamp(t):
    return f"{int(t//3600):02d}:{int(t%3600//60):02d}:{int(t%60):02d},{int((t%1)*1000):03d}"

def generate_srt(base_path):
    json_path = os.path.join(base_path, "subtitles.json")
    srt_path = os.path.join(base_path, "subtitles.srt")

    if not os.path.exists(json_path) or os.path.exists(srt_path):
        return

    with open(json_path) as f:
        subs = json.load(f)

    with open(srt_path, "w") as f:
        for i, s in enumerate(subs, 1):
            f.write(f"{i}\n")
            f.write(f"{format_timestamp(s['start'])} --> {format_timestamp(s['end'])}\n")
            f.write(f"{s['text']}\n\n")


def generate_video(
    base_path,
    voice_name="adam",
    output_name="final_video.mp4",
    ffmpeg_path="ffmpeg",
    fps=1
):
    try:
        audio_file = f"{voice_name}.mp3"
        subtitle_file = "subtitles.srt"
        output_file = output_name

        if not os.path.exists(os.path.join(base_path, audio_file)):
            logging.error("Audio file not found")
            return

        if not os.path.exists(os.path.join(base_path, subtitle_file)):
            logging.error("Subtitle file not found")
            return

        images = sorted(
            f for f in os.listdir(base_path)
            if f.lower().endswith((".png", ".jpg", ".jpeg"))
        )

        if not images:
            logging.error("No images found for video generation")
            return

        img_list = "images.txt"
        with open(os.path.join(base_path, img_list), "w") as f:
            for img in images:
                f.write(f"file '{img}'\n")
                f.write(f"duration {1/fps}\n")
            f.write(f"file '{images[-1]}'\n")

        cmd = [
            ffmpeg_path,
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", img_list,
            "-i", audio_file,
            "-vf", f"subtitles={subtitle_file}",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-shortest",
            output_file
        ]

        cwd = os.getcwd()
        os.chdir(base_path)
        try:
            subprocess.run(cmd, check=True)
            logging.info(f"🎬 Video created: {os.path.join(base_path, output_file)}")
        finally:
            os.chdir(cwd)
            os.remove(os.path.join(base_path, img_list))

    except Exception as e:
        logging.error(f"Video generation error: {e}")


def generate_video_from_subtitles(
    base_path,
    voice_name="adam",
    output_name="final_video.mp4",
    ffmpeg_path="ffmpeg"
):
    try:
        audio_file = f"{voice_name}.mp3"
        subtitle_json = os.path.join(base_path, "subtitles.json")
        # story_json = os.path.join(base_path, "lion.json")
        story_json = os.path.join(base_path, os.path.basename(base_path) + ".json")

        if not all(os.path.exists(os.path.join(base_path, f)) for f in [audio_file]):
            logging.error("Audio file missing")
            return

        if not os.path.exists(subtitle_json) or not os.path.exists(story_json):
            logging.error("Required JSON files missing")
            return

        # Load data
        with open(subtitle_json) as f:
            words = json.load(f)

        with open(story_json) as f:
            story = json.load(f)["image_prompts"]

        # Flatten subtitles into text timeline
        subtitle_text = " ".join(w["text"] for w in words)

        images = sorted(
            f for f in os.listdir(base_path)
            if f.lower().endswith((".png", ".jpg", ".jpeg"))
        )

        if len(images) != len(story):
            logging.warning(
                f"Image count ({len(images)}) != story lines ({len(story)})"
            )

        img_list_path = os.path.join(base_path, "images.txt")

        word_index = 0
        with open(img_list_path, "w") as f:
            for idx, prompt in enumerate(story):
                line_words = prompt["line"].lower().split()

                start_time = words[word_index]["start"]

                for w in words[word_index:]:
                    if w["text"].lower() == line_words[-1]:
                        end_time = w["end"]
                        break
                else:
                    end_time = words[word_index]["end"] + 3  # fallback

                duration = max(0.5, end_time - start_time)

                img = images[min(idx, len(images) - 1)]
                f.write(f"file '{img}'\n")
                f.write(f"duration {duration}\n")

                word_index += len(line_words)

            # FFmpeg requires final image twice
            f.write(f"file '{images[-1]}'\n")

        cmd = [
            ffmpeg_path,
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", "images.txt",
            "-i", audio_file,
            "-vf", "subtitles=subtitles.srt",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-shortest",
            output_name
        ]

        cwd = os.getcwd()
        os.chdir(base_path)
        try:
            subprocess.run(cmd, check=True)
            logging.info(f"🎬 Full-length video created: {output_name}")
        finally:
            os.chdir(cwd)

    except Exception as e:
        logging.error(f"Video generation error: {e}")


# === Runner ===
def run_pipeline(base_path, voice_name="adam", ffmpeg_path="ffmpeg"):
    logging.info(f"Starting pipeline: {base_path}")
    generate_audio_files(base_path, voice_name, ffmpeg_path)
    generate_subtitles(base_path, voice_name)
    generate_srt(base_path)
    generate_video_from_subtitles(base_path, voice_name, ffmpeg_path=ffmpeg_path)

# === Main ===
if __name__ == "__main__":
    BASE_PATH = "./mindset_story"
    FFMPEG_PATH = os.getenv("FFMPEG_PATH", "ffmpeg")
    run_pipeline(BASE_PATH, voice_name="adam", ffmpeg_path=FFMPEG_PATH)
