import os
import json
import requests
import whisper
import torch
import logging
import subprocess
import dotenv
import re

dotenv.load_dotenv()

# Import logger from app if possible, otherwise set up a fallback
try:
    from .app import logger
except ImportError:
    # Fallback if run directly (not through app.py)
    logger = logging.getLogger("story_generator")
    if not logger.handlers:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler()]
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
DEEPGRAM_MAX_CHARS = 2000 # Deepgram's character limit for single requests

device1 = "cuda" if torch.cuda.is_available() else "cpu"
WHISPER_MODEL = whisper.load_model("large", device=device1)

# === Audio Processing ===
def create_script(json_path):
    try:
        logger.info(f"Create_script: loading json file path: {json_path}")
        data = json.load(open(json_path))
        story_lines = [ele.get("line") for ele in data.get("image_prompts",[])]
        return story_lines # Return a list of lines, not a single concatenated string
    except Exception as e:
        logger.info(f'Error creating script: {e}')
        return []

def convert_text_to_speech(text, voice_id, output_path):
    try:
        logger.info(f"Convert_text_to_speech: text length: {len(text)}")
        response = requests.post("https://api.deepgram.com/v1/speak",
            headers={
                "Authorization": f"Token {API_KEY_DEEPGRAM}"
            },
            json={
                "text": text
            }
        )
        if response.status_code == 200:
            with open(output_path, 'wb') as f:
                f.write(response.content)
            logger.info(f'Audio saved: {output_path}')
            return True
        else:
            logger.info(f'Failed to generate audio: {response.status_code} - {response.text}')
            return False
    except Exception as e:
        logger.info(f'Error converting text to speech: {e}')
        return False

def generate_audio_files(base_path, voice_name="adam"):
    try:
        logger.info(f"Generate_audio_files:")
        dir_path = os.path.join(base_path)
        json_files = [f for f in os.listdir(dir_path) if f.endswith(".json") and f != "subtitles.json"]
        story_json_file = json_files[0] if json_files else None
        
        if story_json_file:
            # Get story lines as a list
            story_lines = create_script(os.path.join(dir_path, story_json_file))
            audio_path = os.path.join(dir_path, f"{voice_name}.mp3")
            
            if not os.path.exists(audio_path):
                logger.info(f"Audio file does not exist, generating: {audio_path}")
                
                # --- New Logic for splitting text and concatenating audio ---
                temp_audio_files = []
                current_chunk = ""
                chunk_index = 0

                for line in story_lines:
                    # Add 1 for a potential space between lines if concatenating
                    if len(current_chunk) + len(line) + (1 if current_chunk else 0) <= DEEPGRAM_MAX_CHARS:
                        current_chunk += (line + " ")
                    else:
                        if current_chunk: # Process the current chunk if not empty
                            temp_audio_path = os.path.join(dir_path, f"temp_audio_{chunk_index}.mp3")
                            if convert_text_to_speech(current_chunk.strip(), VOICE_IDS[voice_name], temp_audio_path):
                                temp_audio_files.append(temp_audio_path)
                                chunk_index += 1
                            else:
                                logger.error(f"Failed to generate audio for chunk {chunk_index}.")
                                # Decide how to handle failure: raise error, skip, etc.
                                return 
                        current_chunk = (line + " ") # Start new chunk with current line

                # Process any remaining chunk
                if current_chunk:
                    temp_audio_path = os.path.join(dir_path, f"temp_audio_{chunk_index}.mp3")
                    if convert_text_to_speech(current_chunk.strip(), VOICE_IDS[voice_name], temp_audio_path):
                        temp_audio_files.append(temp_audio_path)
                    else:
                        logger.error(f"Failed to generate audio for final chunk {chunk_index}.")
                        return

                if not temp_audio_files:
                    logger.error("No audio chunks were successfully generated.")
                    return

                # Concatenate all temporary audio files into the final audio file
                concat_list_path = os.path.join(dir_path, "concat_audio_list.txt")
                with open(concat_list_path, "w") as f:
                    for temp_file in temp_audio_files:
                        f.write(f"file '{os.path.basename(temp_file)}'\n") # write relative path for ffmpeg concat

                original_dir = os.getcwd()
                os.chdir(dir_path) # Change directory to where audio files are located
                try:
                    cmd = [
                        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                        "-i", "concat_audio_list.txt", "-c", "copy", os.path.basename(audio_path)
                    ]
                    logger.info(f"Concatenating audio files: {' '.join(cmd)}")
                    subprocess.run(cmd, check=True, shell=False)
                    logger.info(f"Final audio file created: {audio_path}")
                except subprocess.CalledProcessError as e:
                    logger.error(f"Error concatenating audio files: {e}")
                finally:
                    os.chdir(original_dir) # Change back to original directory
                    # Clean up temporary audio files and concat list
                    for temp_file in temp_audio_files:
                        if os.path.exists(temp_file):
                            os.remove(temp_file)
                    if os.path.exists(concat_list_path):
                        os.remove(concat_list_path)
                # --- End new logic ---

            else:
                logger.info(f"Audio file already exists: {audio_path}")
        else:
            logger.warning("No story JSON file found (excluding subtitles.json) to generate script for audio.")
    except Exception as e:
        logger.info(f'Error generating audio files: {e}')

# === Subtitle Processing ===
def extract_word_timings(audio_path):
    try:
        url = 'https://api.deepgram.com/v1/listen'
        headers = {
            'Authorization': f'Token {API_KEY_DEEPGRAM}',
            'Content-Type': 'audio/mp3'
        }
        
        params = {
            'punctuate': 'true', 'diarize': 'false', 'utterances': 'false',
            'model': 'nova', 'language': 'en'
        }
        
        with open(audio_path, 'rb') as audio_file:
            response = requests.post(url, headers=headers, params=params, data=audio_file)
        
        if response.status_code != 200:
            logger.info(f"Error from Deepgram API: {response.status_code} - {response.text}")
            return []
        
        result = response.json()
        words = []
        if 'results' in result and 'channels' in result['results'] and len(result['results']['channels']) > 0:
            channel = result['results']['channels'][0]
            if 'alternatives' in channel and len(channel['alternatives']) > 0:
                alternative = channel['alternatives'][0]
                if 'words' in alternative:
                    for word_info in alternative['words']:
                        words.append({
                            'text': word_info['word'], 'start': float(word_info['start']),
                            'end': float(word_info['end']), 'confidence': float(word_info.get('confidence', 1.0))
                        })
        return words
    except Exception as e:
        logger.info(f"Error extracting word timings with Deepgram: {e}")
        return []

def get_words_and_time(model, speech):
    return extract_word_timings(speech)

def correct_subtitles(text_timestamped,interactive=False):
    len_out = len(text_timestamped)
    for i in range(len_out):
        logger.info(f"{i}, {text_timestamped[i]}")

    if not interactive:
        logger.info("Skipping manual subtitle correction in non-interactive mode.")
        return text_timestamped
    else: # pragma: no cover
        ip_input = input("Enter comma-separated corrections (index:new_word): ")
        to_change = [(int(i.split(':')[0].strip()), i.split(':')[1].strip()) for i in ip_input.split(',')]
        for ind, new_word in to_change:
            logger.info(f'ind: {ind}, new_word: {new_word}')
            if ind < len(text_timestamped) and isinstance(text_timestamped[ind], dict) and len(text_timestamped[ind].values()) == 1:
                original_timing = list(text_timestamped[ind].values())[0]
                text_timestamped[ind] = {new_word: original_timing}  
            else:
                logger.warning(f"Could not correct subtitle at index {ind}, data format issue or index out of bounds.")
        logger.info(f'text_timestamped after correction: {text_timestamped}')
        return text_timestamped

def make_text_timestamped(audio_path, save_path):
    try:
        text_timestamped = get_words_and_time(WHISPER_MODEL, audio_path)
        json.dump(text_timestamped, open(save_path, 'w'))
        return text_timestamped
    except Exception as e:
        logger.info(f'Error making text timestamped: {e}')

def generate_all_subtitles(base_path):
    try:
        dir_path = os.path.join(base_path)
        audio_file = next((f for f in os.listdir(dir_path) if f.endswith(".mp3")), None)
        if audio_file:
            audio_path = os.path.join(dir_path, audio_file)
            subtitles_path = os.path.join(base_path, "subtitles.json")
            if not os.path.exists(subtitles_path):
                logger.info(f"Generating subtitles for {audio_path}")
                make_text_timestamped(audio_path, subtitles_path)
            else:
                logger.info(f"Subtitles file already exists: {subtitles_path}")
        else:
            logger.warning(f"No MP3 file found in {dir_path} to generate subtitles.")
    except Exception as e:
        logger.info(f'Error generating all subtitles: {e}')

# === SRT Creation ===
def format_timestamp(t):
    hours = int(t / 3600)
    minutes = int((t % 3600) / 60)
    seconds = int(t % 60)
    milliseconds = int((t - int(t)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

def create_srt_from_subtitles(subtitles, output_path):
    try:
        logger.info(f"Creating srt from subtitles: {output_path}")
        with open(output_path, 'w') as f:
            for idx, sub in enumerate(subtitles, 1):
                f.write(f"{idx}\n")
                f.write(f"{format_timestamp(sub['start'])} --> {format_timestamp(sub['end'])}\n")
                f.write(f"{sub['text']}\n\n")
    except Exception as e:
        logger.info(f'Error creating srt from subtitles: {e}')

def generate_srt_files(base_path):
    try:
        logger.info(f"Generating srt files for {base_path}")
        subtitle_path = os.path.join(base_path, "subtitles.json")
        srt_path = os.path.join(base_path, "subtitles.srt")
        if os.path.exists(subtitle_path) and not os.path.exists(srt_path):
            logger.info(f"Creating srt from subtitles: {srt_path}")
            subtitles = json.load(open(subtitle_path))
            create_srt_from_subtitles(subtitles, srt_path)
        elif not os.path.exists(subtitle_path):
            logger.warning(f"Subtitles JSON not found at {subtitle_path}, cannot generate SRT.")
        elif os.path.exists(srt_path):
            logger.info(f"SRT file already exists: {srt_path}")
    except Exception as e:
        logger.info(f'Error generating srt files: {e}')

# --- New/Improved normalize_word function ---
def normalize_word(word):
    """
    Normalizes a word for comparison by converting to lowercase,
    removing punctuation from start/end, removing hyphens, and
    removing any internal spaces (e.g., for split contractions).
    """
    word = word.lower()
    # Remove punctuation from start/end of word, but allow internal apostrophes
    word = re.sub(r"^[^\w\d']+|[^\w\d']+$", "", word)
    # Remove hyphens for matching (e.g., "once-vibrant" -> "oncevibrant")
    word = word.replace("-", "")
    # Remove any internal spaces, making "do not" -> "donot"
    word = re.sub(r"\s+", "", word).strip()
    return word
# --- End of New/Improved normalize_word function ---


# === Dynamic Image Duration Calculation ===
def calculate_image_durations_from_story(story_json_path, subtitles_json_path):
    logger.info(f"Calculating image durations from story: {story_json_path} and subtitles: {subtitles_json_path}")
    try:
        with open(story_json_path, 'r', encoding='utf-8') as f:
            story_data = json.load(f)
        with open(subtitles_json_path, 'r', encoding='utf-8') as f:
            subtitles_data = json.load(f)
    except FileNotFoundError as e:
        logger.error(f"Error loading JSON files for duration calculation: {e}")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON for duration calculation: {e}")
        return []

    image_specs = []
    subtitle_word_idx = 0

    if not subtitles_data:
        logger.error("Subtitles data is empty. Cannot calculate durations.")
        return []

    image_prompts = story_data.get("image_prompts", [])
    if not image_prompts:
        logger.warning("No image_prompts found in story JSON.")
        return []

    for i, prompt_entry in enumerate(image_prompts):
        line_text = prompt_entry.get("line")
        if not line_text:
            logger.warning(f"Image prompt {i} has no line text. Skipping.")
            continue

        # Split the line text into words and normalize each
        line_words_original = line_text.split()
        normalized_line_words = [normalize_word(w) for w in line_words_original if normalize_word(w)]

        if not normalized_line_words:
            logger.warning(f"Line for image {i} is empty after normalization: '{line_text}'. Skipping.")
            continue
        
        num_words_in_current_line = len(normalized_line_words)
        
        current_line_matched_subtitle_words = []
        initial_subtitle_word_idx_for_this_line = subtitle_word_idx

        # Attempt to match words from the normalized line against the subtitles
        line_match_successful = True
        for k, target_norm_word in enumerate(normalized_line_words):
            if subtitle_word_idx >= len(subtitles_data):
                logger.warning(f"Ran out of subtitle words while matching line for image {i} (word '{target_norm_word}'): '{line_text}'")
                line_match_successful = False
                break
            
            current_subtitle_norm_word = normalize_word(subtitles_data[subtitle_word_idx]['text'])
            
            if target_norm_word == current_subtitle_norm_word:
                current_line_matched_subtitle_words.append(subtitles_data[subtitle_word_idx])
                subtitle_word_idx += 1
            else:
                logger.warning(f"Word mismatch for image {i}, line '{line_text}'. Expected '{target_norm_word}', got '{current_subtitle_norm_word}' from subtitles. Line will be skipped.")
                line_match_successful = False
                break

        if line_match_successful and len(current_line_matched_subtitle_words) == num_words_in_current_line:
            line_start_time = current_line_matched_subtitle_words[0]['start']
            line_end_time = current_line_matched_subtitle_words[-1]['end']
            duration = line_end_time - line_start_time
            
            if duration <= 0:
                logger.warning(f"Calculated non-positive duration ({duration:.3f}s) for image {i} (line: '{line_text}'). Start: {line_start_time}, End: {line_end_time}. Using 0.1s instead.")
                duration = 0.1 

            image_specs.append({
                'filename': f"{i}.png", 
                'duration': duration
            })
        else:
            # If the line didn't match, we need to reset subtitle_word_idx for the next image's line
            # to prevent a cascade of mismatches if Deepgram's output is out of sync.
            # This is a heuristic and might need adjustment based on typical ASR errors.
            # For simplicity, if a full line doesn't match, we'll try to find the starting point
            # of the *next* expected line in the subtitles to re-sync.
            logger.error(f"Failed to match all words for image {i}, line '{line_text}'. Matched {len(current_line_matched_subtitle_words)}/{num_words_in_current_line}. Skipping duration for this image.")
            
            # Attempt to re-sync: find the first word of the next *story line* in the subtitles
            # This is a complex problem and a simple reset might not always be perfect.
            # For now, let's just leave subtitle_word_idx where it is if a mismatch occurred
            # or try to find the start of the next expected line.
            # The current 'break' statement already prevents advancing subtitle_word_idx on mismatch.
            # The 'initial_subtitle_word_idx_for_this_line' was intended for this, but it was not used for reset.
            # Let's adjust the logic slightly to explicitly revert if the line doesn't match.
            subtitle_word_idx = initial_subtitle_word_idx_for_this_line # Revert for this line if it failed to match completely.
            
            # A more robust re-sync might look ahead in the subtitles for the start of the *next* story line,
            # but that adds significant complexity. Sticking to current logic for now, with better logging.
            
    if not image_specs:
        logger.error("No image durations could be calculated successfully.")
    return image_specs


# === Video Creation ===
def create_video_from_images_with_audio(
    image_dir: str,
    audio_file_abs: str,
    srt_file_abs: str,
    output_file_abs: str,
    image_specs: list, # List of {'filename': '0.png', 'duration': 3.5}
    ffmpeg_executable_path: str = "ffmpeg",
    video_fps: int = 30
):
    logger.info(f"Creating video with dynamic image durations. Number of images: {len(image_specs)}")
    if not image_specs:
        logger.error("No image specifications provided. Cannot create video.")
        return

    original_dir = os.getcwd()
    concat_file_path = None # Initialize

    try:
        audio_filename_relative = os.path.basename(audio_file_abs)
        srt_filename_relative = os.path.basename(srt_file_abs)
        output_filename_relative = os.path.basename(output_file_abs)

        os.chdir(image_dir) # Change to image directory

        # Create concat file
        concat_filename = "concat_list.txt"
        concat_file_path = os.path.join(image_dir, concat_filename) # Absolute path for cleanup
        
        with open(concat_filename, 'w') as f:
            for spec in image_specs:
                # Ensure filenames in concat file are relative to image_dir (which they are, e.g., "0.png")
                f.write(f"file '{spec['filename']}'\n")
                f.write(f"duration {spec['duration']:.3f}\n")
        
        logger.info(f"Generated ffmpeg concat file: {concat_filename} with {len(image_specs)} entries.")

        # Check if SRT file exists before adding subtitle filter
        subtitle_filter = []
        if os.path.exists(srt_filename_relative):
            subtitle_filter = ["-vf", f"subtitles={srt_filename_relative}"]
        else:
            logger.warning(f"SRT file {srt_filename_relative} not found. Video will be created without subtitles.")

        cmd = [
            ffmpeg_executable_path,
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_filename,
            "-i", audio_filename_relative,
        ] + subtitle_filter + [ # Add subtitle filter conditionally
            "-c:v", "libx264",
            "-c:a", "aac",
            "-strict", "experimental",
            "-r", str(video_fps),
            "-pix_fmt", "yuv420p",
            "-shortest",
            output_filename_relative
        ]
        
        logger.info(f"Executing ffmpeg command: {' '.join(cmd)}")
        subprocess.run(cmd, check=True, shell=False)
        logger.info(f"[✓] Video created successfully: {output_file_abs}")

    except subprocess.CalledProcessError as e:
        logger.error(f"[✗] Error during video creation: {e}")
        logger.error(f"Command was: {' '.join(e.cmd)}" if hasattr(e, 'cmd') else "Command details not available.")
        if e.stdout: logger.error(f"ffmpeg stdout: {e.stdout.decode(errors='ignore')}")
        if e.stderr: logger.error(f"ffmpeg stderr: {e.stderr.decode(errors='ignore')}")
    except FileNotFoundError:
        logger.error(f"[✗] Error: The ffmpeg executable ('{ffmpeg_executable_path}') was not found.")
    except Exception as e:
        logger.error(f"[✗] An unexpected error occurred during video creation: {e}")
    finally:
        if concat_file_path and os.path.exists(concat_file_path):
            try:
                os.remove(concat_file_path)
                logger.info(f"Cleaned up temporary concat file: {concat_file_path}")
            except Exception as e_clean:
                logger.error(f"Error cleaning up concat file {concat_file_path}: {e_clean}")
        os.chdir(original_dir)


# === Runner ===
def run_pipeline(base_path, ffmpeg_executable_path: str = "ffmpeg"):
    logger.info(f"Starting pipeline for base_path: {base_path}")
    
    logger.info("Generating audio...")
    generate_audio_files(base_path)

    logger.info("Creating subtitles JSON...")
    generate_all_subtitles(base_path)

    logger.info("Exporting SRT files...")
    generate_srt_files(base_path)

    # Calculate dynamic image durations
    json_files = [f for f in os.listdir(base_path) if f.endswith(".json")]
    story_json_filename = None
    for fname in json_files:
        if fname.lower() != "subtitles.json":
            story_json_filename = fname
            break
    
    if not story_json_filename:
        logger.error(f"Story JSON file (other than subtitles.json) not found in {base_path}. Cannot proceed with dynamic durations.")
        return

    story_json_path = os.path.join(base_path, story_json_filename)
    subtitles_json_path = os.path.join(base_path, "subtitles.json")

    if not os.path.exists(story_json_path):
        logger.error(f"Identified story JSON ({story_json_path}) does not exist.")
        return
    if not os.path.exists(subtitles_json_path):
        logger.error(f"Subtitles JSON ({subtitles_json_path}) does not exist. Cannot calculate dynamic durations.")
        return

    image_specs = calculate_image_durations_from_story(story_json_path, subtitles_json_path)

    if not image_specs:
        logger.error("Failed to calculate image durations. Video creation with dynamic durations aborted.")
        return

    logger.info("Creating video with dynamic durations...")
    audio_file_abs = os.path.join(base_path, "adam.mp3")
    srt_file_abs = os.path.join(base_path, "subtitles.srt")
    output_video_abs = os.path.join(base_path, "story_video_dynamic.mp4")

    if not os.path.exists(audio_file_abs):
        logger.error(f"Audio file {audio_file_abs} not found. Cannot create video.")
        return
    
    # The create_video_from_images_with_audio function now handles the SRT file existence check internally.
    create_video_from_images_with_audio(
        image_dir=base_path,
        audio_file_abs=audio_file_abs,
        srt_file_abs=srt_file_abs,
        output_file_abs=output_video_abs,
        image_specs=image_specs,
        ffmpeg_executable_path=ffmpeg_executable_path
    )

# === Main ===
if __name__ == "__main__":
    base_path = "./mindset_story" 
    
    ffmpeg_path_from_env = os.getenv("FFMPEG_PATH")
    ffmpeg_path_to_use = ffmpeg_path_from_env if ffmpeg_path_from_env else "ffmpeg"
    
    logger.info(f"Using ffmpeg path: {ffmpeg_path_to_use}")
    run_pipeline(base_path, ffmpeg_executable_path=ffmpeg_path_to_use)
