import streamlit as st
import requests

st.title("🧠 Story-to-Multimedia Generator")

story_prompt = st.text_area("Enter your story prompt:")
story_name = st.text_input("Enter a name for your story:")

if st.button("Generate Story"):
    if not story_prompt or not story_name:
        st.error("Please enter both the prompt and story name.")
    else:
        with st.spinner("Generating multimedia story..."):
            response = requests.post(
                "http://0.0.0.0:5000/generate",
                json={"story_prompt": story_prompt, "story_name": story_name}
            )
            if response.ok:
                st.success("✅ Story and multimedia generated!")
            else:
                st.error(f"❌ Failed: {response.json().get('message')}")
