import os
import json
import base64
import requests
from openai import OpenAI
import dotenv
import logging

dotenv.load_dotenv()

# === Logging Config ===
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# === OpenAI Client ===
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# === Stability AI Config ===
STABILITY_API_KEY = os.getenv("STABILITY_API_KEY")
STABILITY_API_URL = os.getenv("STABILITY_API_URL")

# --- STORY GENERATOR PROMPT ---

story_prompt = """
I have listed down some essential elements of writing an engaging short inspirational story.
### Essential Elements of an Engaging Short Inspirational Story

1. **Universal Theme**
2. **Clear Conflict or Challenge**
3. **Positive Resolution**
4. **Emotional Engagement**
5. **Concise and Focused**

Now keeping in mind these elements, write an inspirational short story for the topic: {topic}

PLEASE KEEP THE STORY CRISP AND SHORT.

Story script:
"""

# --- STORY GENERATOR ---

class StoryGenerator:
    def __init__(self, model="gpt-4o", temperature=0.1):
        self.model = model
        self.temperature = temperature

    def generate_story(self, prompt: str, topic: str) -> str:
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert story writer who writes short inspirational stories."
                    },
                    {
                        "role": "user",
                        "content": prompt.format(topic=topic)
                    }
                ],
                temperature=self.temperature
            )
            story = response.choices[0].message.content
            logging.info(f"Story generated successfully")
            return story
        except Exception as e:
            logging.info(f"Error generating story: {e}")
            raise

# --- IMAGE PROMPT GENERATOR ---

class ImagePromptGenerator:
    def __init__(self, model="gpt-4o", temperature=0.1):
        self.model = model
        self.temperature = temperature

    def generate_image_prompts(self, story_script: str) -> list:
        image_prompt = f"""
You have been given a story script below, and you have to create images for the script which will be converted to a video.
For each line in the script given below, give an image prompt that captures the line visually.
Use words such as sharp focus and extremely detailed that result in great images.
Create simple image prompts and do not use a person's name in the prompt.

Complete story script:
'''{story_script}'''

Output should be in JSON format:
[{{"line": "", "image_prompt": ""}}, ...]

Only return the JSON array, nothing else.
"""

        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an English expert."},
                    {"role": "user", "content": image_prompt}
                ],
                temperature=self.temperature
            )

            raw_content = response.choices[0].message.content.strip()

            if raw_content.startswith("```json"):
                raw_content = raw_content.lstrip("```json").rstrip("```").strip()
            elif raw_content.startswith("```"):
                raw_content = raw_content.lstrip("```").rstrip("```").strip()

            logging.info("Image prompts generated successfully")
            return json.loads(raw_content)

        except Exception as e:
            logging.info(f"Error generating image prompts: {e}")
            raise

# --- IMAGE GENERATION ---

def make_body(prompt):
    return {
        "steps": 40,
        "width": 768,
        "height": 1344,
        "seed": 0,
        "cfg_scale": 5,
        "samples": 1,
        "text_prompts": [
            {"text": prompt, "weight": 1},
            {"text": "blurry, bad", "weight": -1}
        ],
    }

def make_image(prompt, img_path):
    body = make_body(prompt)

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {STABILITY_API_KEY}",
    }

    response = requests.post(STABILITY_API_URL, headers=headers, json=body)
    if response.status_code != 200:
        raise Exception(f"Non-200 response: {response.text}")

    data = response.json()
    for image in data["artifacts"]:
        with open(img_path, "wb") as f:
            f.write(base64.b64decode(image["base64"]))

# --- STORY PROCESSOR ---

class StoryProcessor:
    def __init__(self, story_generator: StoryGenerator, image_generator: ImagePromptGenerator):
        self.story_generator = story_generator
        self.image_generator = image_generator

    def process_story(self, story_prompt: str, topic: str):
        story = self.story_generator.generate_story(story_prompt, topic)
        image_prompts = self.image_generator.generate_image_prompts(story)
        return story, image_prompts

    def save_to_file(self, filepath: str, data: dict):
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def run(self, story_prompt: str, story_name: str, topic: str):
        story, image_prompts = self.process_story(story_prompt, topic)

        story_dir = f"./{story_name}"
        os.makedirs(story_dir, exist_ok=True)

        self.save_to_file(
            os.path.join(story_dir, f"{story_name}.json"),
            {
                "story": story,
                "image_prompts": image_prompts
            }
        )

        for i, item in enumerate(image_prompts):
            prompt = item["image_prompt"]
            img_path = os.path.join(story_dir, f"{i}.png")
            logging.info(f"Generating image {i}: {prompt}")
            make_image(prompt, img_path)
            logging.info(f"Image saved: {img_path}")

        logging.info(f"✅ Story and images saved in {story_dir}")

# --- MAIN ---

if __name__ == "__main__":
    story_name = "mindset_story"

    story_gen = StoryGenerator()
    image_gen = ImagePromptGenerator()
    processor = StoryProcessor(story_gen, image_gen)

    processor.run(
        story_prompt=story_prompt,
        story_name=story_name,
        topic="Book Mindset by Carol Dweck"
    )
