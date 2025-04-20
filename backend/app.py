from flask import Flask, request, jsonify
from colab2 import run_pipeline
from colab1 import StoryGenerator, ImagePromptGenerator, StoryProcessor
import os

app = Flask(__name__)

# Initialize once
story_gen = StoryGenerator()
image_gen = ImagePromptGenerator()
processor = StoryProcessor(story_gen, image_gen)

@app.route("/generate", methods=["POST"])
def generate():
    data = request.json
    story_prompt = data.get("story_prompt")
    story_name = data.get("story_name")

    if not story_prompt or not story_name:
        return jsonify({"error": "Missing story_prompt or story_name"}), 400

    try:
        processor.run(story_prompt, story_name)
        run_pipeline("./mindset_story")
        return jsonify({"status": "success", "message": "Story generated."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)