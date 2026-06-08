import streamlit as st
import requests
import uuid
import os

FASTAPI_URL = os.environ.get("FASTAPI_URL", "http://localhost:8000")


st.set_page_config(
    page_title="AI Travel Assistant",
    page_icon="🧭",
    layout="wide"
)

st.title("🧭 AI Travel Itinerary Assistant")
st.caption("Ask about any travel destination — powered by your uploaded guides.")

# ── Session setup ─────────────────────────────────────────
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "pending_general_query" not in st.session_state:
    st.session_state.pending_general_query = None

if "show_help" not in st.session_state:
    st.session_state.show_help = False

# ── Sidebar (NO SCROLL — compact everything) ──────────────
with st.sidebar:

    # ── 1. Upload ─────────────────────────────────────────
    st.header("📁 Upload Guides")
    uploaded_files = st.file_uploader(
        "PDF only",
        type="pdf",
        accept_multiple_files=True,
        label_visibility="collapsed"
    )
    if uploaded_files:
        if st.button("Process Guides", use_container_width=True):
            for uploaded_file in uploaded_files:
                with st.spinner(f"Processing {uploaded_file.name}..."):
                    try:
                        files    = {"file": uploaded_file}
                        response = requests.post(f"{FASTAPI_URL}/upload", files=files)
                        if response.status_code == 200:
                            st.success(f"✅ {uploaded_file.name}")
                        else:
                            st.error(f"❌ Failed: {uploaded_file.name}")
                    except Exception as e:
                        st.error(f"Upload error: {str(e)}")

    st.divider()

    # ── 2. Language selector (compact) ───────────────────
    st.markdown("🌐 **Language**")
    LANGUAGES = {
        "🇬🇧 English"  : "English",
        "🇮🇳 Tamil"    : "Tamil",
        "🇮🇳 Hindi"    : "Hindi",
        "🇮🇳 Telugu"   : "Telugu",
        "🇮🇳 Malayalam": "Malayalam",
        "🇮🇳 Kannada"  : "Kannada",
        "🇫🇷 French"   : "French",
        "🇩🇪 German"   : "German",
        "🇪🇸 Spanish"  : "Spanish",
        "🇯🇵 Japanese" : "Japanese",
        "🇨🇳 Chinese"  : "Chinese",
        "🇦🇪 Arabic"   : "Arabic",
    }
    selected_label    = st.selectbox(
        "lang",
        options=list(LANGUAGES.keys()),
        index=0,
        label_visibility="collapsed"
    )
    selected_language = LANGUAGES[selected_label]

    st.divider()

    # ── 3. Action buttons (side by side) ─────────────────
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ Clear Chat", use_container_width=True):
            requests.post(
                f"{FASTAPI_URL}/clear",
                params={"session_id": st.session_state.session_id}
            )
            st.session_state.messages              = []
            st.session_state.pending_general_query = None
            st.rerun()
    with col2:
        if st.button("🗄️ Clear DB", use_container_width=True):
            with st.spinner("Clearing..."):
                try:
                    r = requests.post(f"{FASTAPI_URL}/clear-db")
                    if r.status_code == 200:
                        st.success("✅ Cleared!")
                    else:
                        st.error("❌ Failed")
                except Exception as e:
                    st.error(f"Error: {str(e)}")

    st.divider()

    # ── 4. Help button → shows popup in main area ─────────
    if st.button("❓ How to Use", use_container_width=True):
        st.session_state.show_help = not st.session_state.show_help

    st.divider()
    st.caption(f"Session: `{st.session_state.session_id[:8]}...`")


# ── Help Popup (shown in main area, not sidebar) ──────────
if st.session_state.show_help:
    with st.container():
        st.markdown("""
<div style="
    background: linear-gradient(135deg, #1e3a5f, #0d2137);
    border: 1px solid #4a9eff;
    border-radius: 16px;
    padding: 24px 28px;
    margin-bottom: 20px;
    color: white;
">

<h3 style="color:#4a9eff; margin-top:0;">❓ How to Use — AI Travel Assistant</h3>

<hr style="border-color:#4a9eff33; margin: 12px 0;">

<h4 style="color:#7ec8ff;">📄 Uploading PDF Guides</h4>
<ul style="margin:0 0 12px 0; padding-left:20px;">
  <li>Click <b>Upload Guides</b> in the sidebar</li>
  <li>Select one or more PDF travel guides</li>
  <li>Click <b>⚡ Process Guides</b> to store them</li>
  <li>Wait for the ✅ success message</li>
</ul>

<h4 style="color:#7ec8ff;">💬 Asking Questions</h4>
<ul style="margin:0 0 12px 0; padding-left:20px;">
  <li>Type your question in the chat box below</li>
  <li>Ask about trips, hotels, food, beaches, activities</li>
  <li>Ask follow-ups like <i>"what about food there?"</i> — AI understands context!</li>
</ul>

<h4 style="color:#7ec8ff;">💾 PDF Memory — Important!</h4>
<ul style="margin:0 0 12px 0; padding-left:20px;">
  <li>Once uploaded, your PDF is <b>stored permanently</b> in the database</li>
  <li>You do <b>NOT</b> need to re-upload next time you open the app</li>
  <li>Just open the app and ask questions directly!</li>
  <li>Use <b>🗄️ Clear DB</b> only when you want to remove old PDFs</li>
  <li>After clearing, re-upload your PDFs fresh</li>
</ul>

<h4 style="color:#7ec8ff;">🌐 Language</h4>
<ul style="margin:0 0 12px 0; padding-left:20px;">
  <li>Select your preferred language from the dropdown</li>
  <li>Ask in <b>any language</b> — AI answers in your selected language</li>
</ul>

<h4 style="color:#7ec8ff;">🗑️ Clear Chat vs 🗄️ Clear DB</h4>
<table style="width:100%; border-collapse:collapse; font-size:13px;">
  <tr style="background:#ffffff15;">
    <th style="padding:6px 10px; text-align:left; color:#4a9eff;">Button</th>
    <th style="padding:6px 10px; text-align:left; color:#4a9eff;">What it does</th>
    <th style="padding:6px 10px; text-align:left; color:#4a9eff;">PDF data safe?</th>
  </tr>
  <tr>
    <td style="padding:6px 10px;">🗑️ Clear Chat</td>
    <td style="padding:6px 10px;">Clears chat messages only</td>
    <td style="padding:6px 10px;">✅ Yes — PDF stays</td>
  </tr>
  <tr style="background:#ffffff10;">
    <td style="padding:6px 10px;">🗄️ Clear DB</td>
    <td style="padding:6px 10px;">Wipes ALL uploaded PDFs</td>
    <td style="padding:6px 10px;">❌ No — must re-upload</td>
  </tr>
</table>

</div>
""", unsafe_allow_html=True)

        # Close button
        if st.button("✖ Close Help", type="primary"):
            st.session_state.show_help = False
            st.rerun()

        st.markdown("---")


# ── Chat history ──────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

if not st.session_state.messages:
    with st.chat_message("assistant"):
        st.markdown(
            "👋 Hello! I'm your AI Travel Assistant. "
            "Upload travel guide PDFs, then ask me anything — "
            "even follow-ups like *'what about food there?'* and I'll figure out where you mean! "
            "Click **❓ How to Use** in the sidebar for full guide."
        )

# ── Display chat history ──────────────────────────────────
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant" and message.get("rewritten_query"):
            original  = message.get("original_query", "")
            rewritten = message["rewritten_query"]
            if rewritten.lower().strip() != original.lower().strip():
                st.caption(f"🔍 Searched as: \"{rewritten}\"")


# ── Chat input ────────────────────────────────────────────
if prompt := st.chat_input("Ask about any destination..."):

    # ══ CASE 1: Waiting for YES / NO ═════════════════════
    if st.session_state.pending_general_query is not None:

        original_query = st.session_state.pending_general_query
        user_reply     = prompt.strip().lower()

        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        st.session_state.pending_general_query = None

        YES_WORDS = {
            "yes", "yeah", "sure", "ok", "okay", "yep", "please", "y",
            "是的", "是", "好的", "好", "要", "对", "行",
            "ஆம்", "ஆமா", "சரி", "ஓகே", "ஆமாம்",
            "हाँ", "हां", "हा", "जी", "जी हाँ", "ठीक है",
            "అవును", "సరే", "అవు",
            "അതെ", "ശരി", "ഓക്കേ",
            "ಹೌದು", "ಸರಿ", "ಓಕೆ",
            "oui", "ouais", "bien sûr",
            "ja", "jawohl", "natürlich",
            "sí", "si", "claro", "bueno",
            "はい", "うん", "そうです",
            "نعم", "أجل", "تمام", "موافق",
        }
        user_said_yes = any(w in user_reply for w in YES_WORDS)

        if user_said_yes:
            with st.chat_message("assistant"):
                with st.spinner("Answering from general knowledge..."):
                    try:
                        response = requests.post(
                            f"{FASTAPI_URL}/ask",
                            json={
                                "query":       original_query,
                                "session_id":  st.session_state.session_id,
                                "use_general": True,
                                "language":    selected_language
                            }
                        )
                        if response.status_code == 200:
                            data            = response.json()
                            answer          = data["response"]
                            rewritten_query = data.get("rewritten_query", original_query)
                            st.markdown(answer)
                            st.caption("ℹ️ Answered from general knowledge — upload a PDF for guide-based answers.")
                            if rewritten_query.lower().strip() != original_query.lower().strip():
                                st.caption(f"🔍 Searched as: \"{rewritten_query}\"")
                            st.session_state.messages.append({
                                "role":            "assistant",
                                "content":         answer,
                                "rewritten_query": rewritten_query,
                                "original_query":  original_query
                            })
                        else:
                            err = "⚠️ Server error. Please try again."
                            st.error(err)
                            st.session_state.messages.append({"role": "assistant", "content": err})
                    except Exception as e:
                        err = f"⚠️ Could not reach the server: {e}"
                        st.error(err)
                        st.session_state.messages.append({"role": "assistant", "content": err})
        else:
            no_msg = "No problem! Upload a PDF travel guide for this destination and I'll give you a detailed answer from it."
            with st.chat_message("assistant"):
                st.markdown(no_msg)
            st.session_state.messages.append({"role": "assistant", "content": no_msg})

    # ══ CASE 2: Normal fresh query ════════════════════════
    else:
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    response = requests.post(
                        f"{FASTAPI_URL}/ask",
                        json={
                            "query":      prompt,
                            "session_id": st.session_state.session_id,
                            "language":   selected_language
                        }
                    )
                    if response.status_code == 200:
                        data            = response.json()
                        answer          = data["response"]
                        rewritten_query = data.get("rewritten_query", prompt)

                        if answer is None:
                            confirm_msg = (
                                "I don't have a PDF travel guide for this destination.\n\n"
                                "Would you like me to answer based on my **general knowledge**? *(yes / no)*\n\n"
                                "⚠️ Please respond only with yes or no so I can continue."
                            )
                            st.markdown(confirm_msg)
                            st.session_state.messages.append({
                                "role":    "assistant",
                                "content": confirm_msg
                            })
                            st.session_state.pending_general_query = prompt
                        else:
                            st.markdown(answer)
                            if rewritten_query.lower().strip() != prompt.lower().strip():
                                st.caption(f"🔍 Searched as: \"{rewritten_query}\"")
                            st.session_state.messages.append({
                                "role":            "assistant",
                                "content":         answer,
                                "rewritten_query": rewritten_query,
                                "original_query":  prompt
                            })
                    else:
                        err = "⚠️ Server error. Please try again."
                        st.error(err)
                        st.session_state.messages.append({"role": "assistant", "content": err})
                except Exception as e:
                    err = f"⚠️ Could not reach the server: {e}"
                    st.error(err)
                    st.session_state.messages.append({"role": "assistant", "content": err})