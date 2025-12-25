import streamlit as st
import requests
import os
import dotenv
import urllib.parse
import time

# Load environment variables
dotenv.load_dotenv()

# Get base URL from environment
FLASK_API_BASE_URL = os.getenv("FLASK_API_BASE_URL", "http://backend-service:5151")

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
                    st.success("✅ Story generation started! Processing in background...")
                    
                    # Poll for video completion
                    status_placeholder = st.empty()
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    max_attempts = 600  # 5 minutes max (300 * 1 second)
                    attempt = 0
                    
                    while attempt < max_attempts:
                        # Check video status
                        status_url = f"{FLASK_API_BASE_URL}/video/status/{encoded_name}"
                        try:
                            status_response = requests.get(status_url, timeout=10)
                            if status_response.ok:
                                status_data = status_response.json()
                                status = status_data.get("status", "unknown")
                                ready = status_data.get("ready", False)
                                
                                # Update progress
                                progress = min(attempt / max_attempts, 0.95)  # Cap at 95% until ready
                                progress_bar.progress(progress)
                                
                                if ready:
                                    progress_bar.progress(1.0)
                                    status_text.success("✅ Video is ready!")
                                    
                                    # Get video data for download
                                    download_url = f"{FLASK_API_BASE_URL}/video/download/{encoded_name}"
                                    try:
                                        download_response = requests.get(download_url, timeout=30)
                                        if download_response.ok:
                                            # Trigger download using Streamlit's download button
                                            video_filename = f"{story_name}_video.mp4"
                                            st.download_button(
                                                label="📥 Download Video",
                                                data=download_response.content,
                                                file_name=video_filename,
                                                mime="video/mp4"
                                            )
                                            st.success(f"🎬 Video '{video_filename}' is ready for download!")
                                            break
                                        else:
                                            status_text.error("❌ Failed to download video")
                                    except Exception as e:
                                        status_text.error(f"⚠️ Download error: {str(e)}")
                                    break
                                elif status == "processing":
                                    status_text.info(f"⏳ Processing... (Attempt {attempt + 1}/{max_attempts})")
                                elif status == "error":
                                    status_text.error("❌ Error generating video")
                                    break
                                else:
                                    status_text.info(f"⏳ Waiting for processing to start... (Attempt {attempt + 1}/{max_attempts})")
                        except requests.exceptions.RequestException as e:
                            status_text.warning(f"⚠️ Status check failed: {str(e)}")
                        
                        time.sleep(1)  # Wait 1 second before next check
                        attempt += 1
                    
                    if attempt >= max_attempts:
                        status_text.warning("⏱️ Timeout: Video generation is taking longer than expected. Please check back later.")
                        
                else:
                    try:
                        st.error(f"❌ Failed: {response.json().get('message', 'Unknown error')}")
                    except:
                        st.error("❌ Failed to generate story.")
            except Exception as e:
                st.error(f"⚠️ Error: {str(e)}")

