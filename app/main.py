import streamlit as st
from router import classify_query
from faq import ingest_faq_data,faq_chain
from pathlib import Path
from sql import sql_chain


# Base directory of main.py
BASE_DIR = Path(__file__).parent

faqs_path = Path(__file__).parent / "resources/faq_data.csv"
ingest_faq_data(faqs_path)

# Logo path
LOGO_PATH = BASE_DIR / "img.png"

def ask(query):
    normalized_query = query.strip()
    lowered_query = normalized_query.casefold()

    if lowered_query in {"hi", "hello", "hey", "good morning", "good afternoon", "good evening"}:
        return "Hello! I can help you find products or answer questions about orders, payments, returns, and refunds."
    if lowered_query in {"thanks", "thank you", "thx"}:
        return "You're welcome!"

    try:
        route, normalized_query = classify_query(normalized_query)
        if route == 'faq':
            return faq_chain(normalized_query)
        if route == 'sql':
            return sql_chain(normalized_query)
        return "I can help you search for products or answer questions about orders, payments, returns, and refunds."
    except Exception:
        return "I couldn't process that request right now. Please try asking in a different way."

# st.image("img.png", width=50)
# st.title("E commerce chatbot")

col1, col2 = st.columns([1, 5])
with col1:
    st.image(str(LOGO_PATH), width=80)
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


