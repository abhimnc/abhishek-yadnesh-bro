import streamlit as st
import requests

# Simulate a session (in production, use login-based auth + DB)
if "prompt_count" not in st.session_state:
    st.session_state.prompt_count = 0
if "paid" not in st.session_state:
    st.session_state.paid = False

st.title("🧠 Story-to-Reel Generator")

story_prompt = st.text_area("Enter your story prompt:")
story_name = st.text_input("Enter a name for your story:")

# Show user's usage
st.info(f"You've used {st.session_state.prompt_count} / 2 free prompts.")

def trigger_payment():
    # Simulate Juspay link creation (you'd integrate Juspay's API here)
    payment_link = "https://juspay.in/fake_payment_link"
    st.markdown(f"🔗 [Click here to pay ₹20 to unlock more prompts]({payment_link})")
    # In reality, after payment success, you’d update the backend or session
    # Simulating payment success for now
    if st.button("I've Paid"):
        st.session_state.paid = True
        st.success("🎉 Payment confirmed! You can now generate unlimited stories.")

if st.button("Generate Story"):
    if not story_prompt or not story_name:
        st.error("Please enter both the prompt and story name.")
    else:
        if st.session_state.prompt_count < 2 or st.session_state.paid:
            with st.spinner("Generating multimedia story..."):
                response = requests.post(
                    "http://142.170.89.97:23028/generate/{story_prompt}/{story_name}/",
                    headers={"Content-Type": "application/json"}
                )
                if response.ok:
                    st.success("✅ Story and multimedia generated!")
                    st.session_state.prompt_count += 1
                else:
                    st.error(f"❌ Failed: {response.json().get('message')}")
        else:
            st.warning("⚠️ You have used your 2 free prompts.")
            trigger_payment()
