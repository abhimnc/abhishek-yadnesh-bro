import streamlit as st
import requests
import os
import dotenv
import urllib.parse

# Load environment variables
dotenv.load_dotenv()

# Get base URL from environment
FLASK_API_BASE_URL = os.getenv("FLASK_API_BASE_URL", "http://35.192.14.249:5000")

st.title("🧠 Story-to-Reel Generator")

story_prompt = st.text_area("Enter your story prompt:")
story_name = st.text_input("Enter a name for your story:")
topic = st.text_input("Enter a topic for your story:")

if st.button("Generate Story"):
    if not story_prompt or not story_name:
        st.error("Please enter both the prompt and story name.")
    else:
        with st.spinner("Generating multimedia story..."):
            try:
                # Encode the story prompt and name for safe URL usage
                encoded_prompt = urllib.parse.quote(story_prompt)
                encoded_name = urllib.parse.quote(story_name)
                encoded_topic = urllib.parse.quote(topic)

                # Construct the URL
                url = f"{FLASK_API_BASE_URL}/generate/{encoded_prompt}/{encoded_name}/{encoded_topic}"

                # Send POST request
                response = requests.post(
                    url,
                    headers={"Content-Type": "application/json"}
                )

                if response.ok:
                    st.success("✅ Story and multimedia generated!")
                else:
                    try:
                        st.error(f"❌ Failed: {response.json().get('message', 'Unknown error')}")
                    except:
                        st.error("❌ Failed to generate story.")
            except Exception as e:
                st.error(f"⚠️ Error: {str(e)}")

