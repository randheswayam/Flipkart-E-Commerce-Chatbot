import streamlit as st
from router import router
from faq import ingest_faq_data,faq_chain
from pathlib import Path
from sql import sql_chain


faqs_path = Path(__file__).parent / "resources/faq_data.csv"
img_path = Path(__file__).parent / "img.png"
ingest_faq_data(faqs_path)

def ask(query):
    route = router(query).name
    if route == 'faq':
        return faq_chain(query)
    elif route == 'sql':
        return sql_chain(query)
    else:
        return f"Route {route} not implemented yet"

# st.title("E commerce chatbot")
col1, col2 = st.columns([1, 5])
with col1:
    # st.image("img.png", width=80)
    st.image(str(img_path), width=80)
with col2:
    st.title("E Commerce Chatbot")


query = st.chat_input("Write your query")

if "messages" not in st.session_state:
    st.session_state["messages"] = []

for message in st.session_state.messages:
    with st.chat_message(message['role']):
        st.markdown(message['content'])

if query:
    with st.chat_message("user"):
        st.markdown(query)
    st.session_state.messages.append({"role":"user", "content": query})

    response = ask(query)
    with st.chat_message("assistant"):
        st.markdown(response)
    st.session_state.messages.append({"role":"assistant", "content": response})


