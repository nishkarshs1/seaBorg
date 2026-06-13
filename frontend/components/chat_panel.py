import streamlit as st
import requests
import os

def render_chat() -> dict | None:
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    user_input = st.chat_input("Ask about ocean data... e.g. temperature at 500m")
    
    if user_input:
        # Add user message to history
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        backend_url = os.environ.get("BACKEND_URL", "http://localhost:8001")
        api_endpoint = f"{backend_url}/api/chat"
        
        with st.chat_message("assistant"):
            with st.spinner("🔍 Searching ARGO data..."):
                try:
                    response = requests.post(
                        api_endpoint,
                        json={"message": user_input},
                        timeout=60
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        st.markdown(data.get("answer", "No text response."))
                        st.session_state.messages.append({"role": "assistant", "content": data.get("answer", "")})
                        return data
                    else:
                        st.error(f"Error {response.status_code}: {response.text}")
                except requests.exceptions.RequestException as e:
                    st.error(f"Failed to connect to backend: {e}")
                    
    return None
