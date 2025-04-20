import subprocess
import os

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
        print(f"[✓] Video created successfully: {output_file}")
    except subprocess.CalledProcessError as e:
        print("[✗] Error during video creation:", e)
    finally:
        os.chdir(original_dir)
