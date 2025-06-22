import streamlit as st
import requests
import os
import dotenv

dotenv.load_dotenv()

FLASK_API_BASE_URL = os.getenv("FLASK_API_BASE_URL")

st.title("🧠 Story-to-Reel Generator")

story_prompt = st.text_area("Enter your story prompt:")
story_name = st.text_input("Enter a name for your story:")

if st.button("Generate Story"):
    if not story_prompt or not story_name:
        st.error("Please enter both the prompt and story name.")
    else:
        with st.spinner("Generating multimedia story..."):
            try:
                url = f"{FLASK_API_BASE_URL}/generate/{story_prompt}/{story_name}/"
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
