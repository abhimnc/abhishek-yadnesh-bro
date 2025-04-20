import os
import json
import base64
import requests
from openai import OpenAI

# Initialize OpenAI client
client = OpenAI(api_key="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")

# Stability API Key
STABILITY_API_KEY = "sk-0fKcMzsaSqDav7GQU1WdNZm18Ga98iRoPHjsPcoZpRJldwpa"

# --- STORY GENERATOR ---

class StoryGenerator:
    def __init__(self, model="gpt-4o", temperature=0.1):
        self.model = model
        self.temperature = temperature

    def generate_story(self, prompt: str) -> str:
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert story writer who writes short inspirational stories."},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature
            )
            return response.choices[0].message.content
        except Exception as e:
            print("Error generating story:", e)
            raise

# --- IMAGE PROMPT GENERATOR ---

class ImagePromptGenerator:
    def __init__(self, model="gpt-4o", temperature=0.1):
        self.model = model
        self.temperature = temperature

    def generate_image_prompts(self, story_script: str) -> list:
        image_prompt = f"""
        You have been given a story script below, and you have to create images for the script which will be converted to a video.
        The script has been then split into phrases. For each phrase line given below, give an image prompt that captures the line visually.
        Use words such as sharp focus and extremely detailed that result in great images.
        Create simple image prompts and do not use a person's name in the prompt.

        Complete story script:
        '''{story_script}'''

        Output should be in JSON format:
        [{{"line": "", "image_prompt": ""}}, ...]
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
            return json.loads(raw_content)
        except Exception as e:
            print("Error generating image prompts:", e)
            raise

# --- IMAGE GENERATOR ---

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
    url = "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image"

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {STABILITY_API_KEY}",
    }

    response = requests.post(url, headers=headers, json=body)
    if response.status_code != 200:
        raise Exception("Non-200 response: " + str(response.text))

    data = response.json()
    for image in data["artifacts"]:
        with open(img_path, "wb") as f:
            f.write(base64.b64decode(image["base64"]))

# --- STORY PROCESSOR ---

class StoryProcessor:
    def __init__(self, story_generator: StoryGenerator, image_generator: ImagePromptGenerator):
        self.story_generator = story_generator
        self.image_generator = image_generator

    def process_story(self, story_prompt: str):
        story = self.story_generator.generate_story(story_prompt)
        image_prompts = self.image_generator.generate_image_prompts(story)
        return story, image_prompts

    def save_to_file(self, filepath: str, data: dict):
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def run(self, story_prompt: str, story_name: str):
        story, image_prompts = self.process_story(story_prompt)
        story_dir = f"./{story_name}"
        os.makedirs(story_dir, exist_ok=True)

        # Save story & prompts
        self.save_to_file(os.path.join(story_dir, f"{story_name}.json"), {
            "story": story,
            "image_prompts": image_prompts
        })

        # Generate images
        for i, item in enumerate(image_prompts):
            prompt = item["image_prompt"]
            img_path = os.path.join(story_dir, f"{i}.png")
            make_image(prompt, img_path)

        print(f"✅ Story and images saved in {story_dir}")

# --- MAIN EXECUTION ---

if __name__ == "__main__":
    story_prompt = """
    First write down the most essential elements of writing an engaging short inspirational story.
    Now keeping in mind these elements, write an inspirational short story from the book Mindset by Carol Dweck.
    """

    story_name = "mindset_story"

    story_gen = StoryGenerator()
    image_gen = ImagePromptGenerator()
    processor = StoryProcessor(story_gen, image_gen)

    processor.run(story_prompt, story_name)
