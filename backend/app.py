from flask import Flask, request, jsonify
from colab2 import run_pipeline
from colab1 import StoryGenerator, ImagePromptGenerator, StoryProcessor
import threading
import queue
import os
import time
import logging
app = Flask(__name__)

# Initialize once
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
 
        story_prompt, story_name = item
        try:
            logging.info(f"[Worker] Processing story: {story_name}")
            processor.run(story_prompt, story_name)
            run_pipeline(f"{story_name}")
            logging.info(f"[Worker] Completed: {story_name}")
           
        except Exception as e:
            logging.info(f"[Worker] Error processing story {story_name}: {e}")
        

# Start the background worker thread
worker_thread = threading.Thread(target=worker, daemon=True)
worker_thread.start()

@app.route("/generate/<string:story_prompt>/<string:story_name>/", methods=["GET", "POST"])
def generate(story_prompt, story_name):
    if not story_prompt or not story_name:
        return jsonify({"error": "Missing story_prompt or story_name"}), 400

    try:
        request_queue.put((story_prompt, story_name))
        return jsonify({"status": "queued", "message": f"Story '{story_name}' added to queue."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok"}), 200

@app.route("/queue_size", methods=["GET"])
def queue_size():
    return jsonify({"queue_size": request_queue.qsize()}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
