from flask import Flask, request, jsonify
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

def worker():
    while True:
        time.sleep(1)  # Sleep to prevent busy waiting

        if request_queue.empty():
            continue
        item = request_queue.get()
 
        story_prompt, story_name, topic = item
        try:
            logging.info(f"[Worker] Processing story: {story_name}")
            processor.run(story_prompt, story_name,topic)
            run_pipeline(f"{story_name}")
            logging.info(f"[Worker] Completed: {story_name}")
           
        except Exception as e:
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


# ---------------- MAIN ----------------
if __name__ == "__main__":
    logging.info("Starting API on 0.0.0.0:5151")
    # Start the background worker thread
    worker_thread = threading.Thread(target=worker, daemon=True)
    worker_thread.start()

    app.run(host="0.0.0.0", port=5151, debug=False, use_reloader=False)
