from flask import Flask, request, jsonify, send_file
import threading
import queue
import time
import logging
import urllib.parse
import sys
import os
from colab1 import StoryGenerator, ImagePromptGenerator, StoryProcessor
# from colab2 import run_pipeline

from colab2 import run_pipeline
# ---------------- APP ----------------
app = Flask(__name__)



story_gen = StoryGenerator()
image_gen = ImagePromptGenerator()
processor = StoryProcessor(story_gen, image_gen)

# Queue and Lock
request_queue = queue.Queue()

# Track video status: "processing", "completed", "error"
video_status = {}
status_lock = threading.Lock()

def worker():
    while True:
        time.sleep(1)  # Sleep to prevent busy waiting

        if request_queue.empty():
            continue
        item = request_queue.get()
 
        story_prompt, story_name, topic = item
        # Mark as processing
        with status_lock:
            video_status[story_name] = "processing"
        
        try:
            logging.info(f"[Worker] Processing story: {story_name}")
            processor.run(story_prompt, story_name, topic)
            run_pipeline(f"{story_name}")
            
            # Check if video file exists
            video_path = os.path.join(story_name, "final_video.mp4")
            if os.path.exists(video_path):
                with status_lock:
                    video_status[story_name] = "completed"
                logging.info(f"[Worker] Completed: {story_name} - Video ready at {video_path}")
            else:
                with status_lock:
                    video_status[story_name] = "error"
                logging.error(f"[Worker] Video file not found: {video_path}")
           
        except Exception as e:
            with status_lock:
                video_status[story_name] = "error"
            logging.error(f"[Worker] Error processing story {story_name}: {e}")
        



@app.route("/generate/<string:story_prompt>/<string:story_name>/<string:topic>", methods=["GET", "POST"])
def generate(story_prompt, story_name, topic):
    if not story_prompt or not story_name:
        return jsonify({"error": "Missing story_prompt or story_name"}), 400

    try:
        request_queue.put((story_prompt, story_name, topic))
        return jsonify({"status": "queued", "message": f"Story '{story_name}' added to queue."})
    except Exception as e:
        logging.error(f"Error queuing story: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/queue_size", methods=["GET"])
def queue_size():
    return jsonify({"queue_size": request_queue.qsize()}), 200


@app.route("/video/status/<string:story_name>", methods=["GET"])
def video_status_check(story_name):
    """Check if video is ready for download"""
    story_name = urllib.parse.unquote(story_name)
    with status_lock:
        status = video_status.get(story_name, "not_found")
    
    video_path = os.path.join(story_name, "final_video.mp4")
    exists = os.path.exists(video_path)
    
    return jsonify({
        "status": status,
        "ready": status == "completed" and exists,
        "story_name": story_name
    }), 200


@app.route("/video/download/<string:story_name>", methods=["GET"])
def download_video(story_name):
    """Download the generated video"""
    story_name = urllib.parse.unquote(story_name)
    video_path = os.path.join(story_name, "final_video.mp4")
    
    if not os.path.exists(video_path):
        return jsonify({"error": "Video not found"}), 404
    
    try:
        return send_file(
            video_path,
            as_attachment=True,
            download_name=f"{story_name}_video.mp4",
            mimetype="video/mp4"
        )
    except Exception as e:
        logging.error(f"Error downloading video: {e}")
        return jsonify({"error": str(e)}), 500


# ---------------- MAIN ----------------
if __name__ == "__main__":
    logging.info("Starting API on 0.0.0.0:5151")
    # Start the background worker thread
    worker_thread = threading.Thread(target=worker, daemon=True)
    worker_thread.start()

    app.run(host="0.0.0.0", port=5151, debug=False, use_reloader=False)
