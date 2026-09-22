import re
import time
import json
import requests
import pandas as pd
import streamlit as st

# =====================================================
# PAGE CONFIG
# =====================================================
st.set_page_config(
    page_title="WhatsApp Business Broadcast Console",
    layout="centered"
)

# =====================================================
# PASSWORD PROTECTION
# =====================================================
APP_PASSWORD = "12345$"

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown("## 🔐 Secure Access")
    pwd = st.text_input("Enter application password", type="password")
    if st.button("Login"):
        if pwd == APP_PASSWORD:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Invalid password")
    st.stop()

# =====================================================
# UI STYLING
# =====================================================
st.markdown("""
<style>
.stApp { background-color: #ffffff; }
.preview-box {
    border: 1px solid #dcdcdc;
    border-radius: 10px;
    padding: 16px;
    background-color: #fafafa;
}
.preview-title {
    font-weight: 600;
    margin-bottom: 8px;
}
</style>
""", unsafe_allow_html=True)

st.title("📲 WhatsApp Business Broadcast System")

# =====================================================
# HELPERS
# =====================================================
E164_RE = re.compile(r"^\+[1-9]\d{7,14}$")

def normalize_phone(value):
    if value is None:
        return None
    s = str(value).strip()
    s = re.sub(r"[ \-\(\)]", "", s)
    if s.startswith("00"):
        s = "+" + s[2:]
    if s.isdigit():
        s = "+" + s
    return s if E164_RE.match(s) else None

def upload_media(token, phone_number_id, file_bytes, filename, mime_type):
    url = f"https://graph.facebook.com/v20.0/{phone_number_id}/media"
    headers = {"Authorization": f"Bearer {token}"}
    files = {"file": (filename, file_bytes, mime_type)}
    data = {"messaging_product": "whatsapp"}
    r = requests.post(url, headers=headers, files=files, data=data, timeout=60)
    return r.json().get("id")

def send_message(token, phone_number_id, payload):
    url = f"https://graph.facebook.com/v20.0/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    r = requests.post(url, headers=headers, json=payload, timeout=60)
    try:
        return r.status_code, r.json()
    except Exception:
        return r.status_code, {"raw": r.text}

# =====================================================
# SIDEBAR – API CREDENTIALS
# =====================================================
st.sidebar.header("🔑 WhatsApp API Credentials")
access_token = st.sidebar.text_input("Access Token", type="password")
phone_number_id = st.sidebar.text_input("Phone Number ID", type="password")

# =====================================================
# MESSAGE BUILDER – SINGLE TAB
# =====================================================
st.subheader("🧩 Message Builder")

# ---------- NORMAL MESSAGE ----------
st.markdown("### ✉️ Normal Message")

message_text = st.text_area(
    "Message Text",
    height=120,
    placeholder="Hello! This is an official WhatsApp message."
)

media_file = st.file_uploader(
    "Optional Image / Video",
    type=["jpg", "jpeg", "png", "webp", "mp4", "mov"]
)

st.divider()

# ---------- REACTION / POLL ----------
st.markdown("### 👍 Reaction / Poll (optional)")
poll_enabled = st.checkbox("Enable Reaction / Poll")

reaction_labels = []
if poll_enabled:
    r1 = st.text_input("Option 1", value="👍 Yes")
    r2 = st.text_input("Option 2", value="👎 No")
    r3 = st.text_input("Option 3 (optional)")
    reaction_labels = [r for r in [r1, r2, r3] if r.strip()]

st.divider()

# ---------- SURVEY ----------
st.markdown("### 📊 Survey (optional)")
survey_enabled = st.checkbox("Enable Survey")

survey_questions = []
if survey_enabled:
    q = st.text_input("Survey Question")
    opts = st.text_input("Options (comma separated)", "Yes,No")
    if q:
        survey_questions.append({
            "question": q,
            "options": [o.strip() for o in opts.split(",") if o.strip()]
        })

# =====================================================
# PREVIEW
# =====================================================
st.subheader("👀 Live Preview")

with st.container():
    st.markdown("<div class='preview-box'>", unsafe_allow_html=True)
    st.markdown("<div class='preview-title'>WhatsApp Message Preview</div>", unsafe_allow_html=True)

    if message_text:
        st.markdown(message_text)

    if media_file:
        if media_file.type.startswith("image"):
            st.image(media_file)
        else:
            st.video(media_file)

    if poll_enabled and reaction_labels:
        st.markdown("**Poll Options:** " + " | ".join(reaction_labels))

    if survey_enabled and survey_questions:
        st.markdown(f"**Survey Question:** {survey_questions[0]['question']}")
        st.markdown("Options: " + " | ".join(survey_questions[0]["options"]))

    st.markdown("</div>", unsafe_allow_html=True)

# =====================================================
# RECIPIENT UPLOAD
# =====================================================
st.subheader("📄 Recipient List")

uploaded_file = st.file_uploader(
    "Upload CSV / Excel (phone / number / mobile)",
    type=["csv", "xlsx"]
)

recipients = []

if uploaded_file:
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith(".csv") else pd.read_excel(uploaded_file)
    phone_col = next((c for c in df.columns if c.lower() in ["phone","number","mobile","to","whatsapp"]), None)
    if phone_col:
        df["normalized"] = df[phone_col].apply(normalize_phone)
        recipients = df["normalized"].dropna().tolist()
        st.dataframe(df[[phone_col, "normalized"]])
    else:
        st.error("Phone column not found")

delay = st.number_input("Delay between messages (seconds)", 0.0, 10.0, 0.0, 0.1)

# =====================================================
# SEND BROADCAST
# =====================================================
if st.button("🚀 Send Broadcast"):
    if not access_token or not phone_number_id:
        st.error("Missing API credentials")
        st.stop()

    if not recipients:
        st.error("No valid recipients")
        st.stop()

    media_id = None
    if media_file:
        media_id = upload_media(
            access_token.strip(),
            phone_number_id.strip(),
            media_file.getvalue(),
            media_file.name,
            media_file.type
        )

    results = []
    progress = st.progress(0)

    for i, phone in enumerate(recipients, start=1):
        payload = {
            "messaging_product": "whatsapp",
            "to": phone
        }

        # PRIORITY 1 – SURVEY
        if survey_enabled and survey_questions:
            q = survey_questions[0]
            payload["type"] = "interactive"
            payload["interactive"] = {
                "type": "button",
                "body": {"text": q["question"][:1024]},
                "action": {
                    "buttons": [
                        {
                            "type": "reply",
                            "reply": {"id": f"survey_{idx}", "title": opt[:20]}
                        }
                        for idx, opt in enumerate(q["options"], start=1)
                    ]
                }
            }

        # PRIORITY 2 – POLL
        elif poll_enabled and reaction_labels:
            payload["type"] = "interactive"
            payload["interactive"] = {
                "type": "button",
                "body": {"text": message_text[:1024]},
                "action": {
                    "buttons": [
                        {
                            "type": "reply",
                            "reply": {"id": f"poll_{idx}", "title": lbl[:20]}
                        }
                        for idx, lbl in enumerate(reaction_labels, start=1)
                    ]
                }
            }

        # PRIORITY 3 – MEDIA
        elif media_id:
            msg_type = "image" if media_file.type.startswith("image") else "video"
            payload["type"] = msg_type
            payload[msg_type] = {
                "id": media_id,
                "caption": message_text[:1024]
            }

        # PRIORITY 4 – TEXT
        else:
            payload["type"] = "text"
            payload["text"] = {"body": message_text}

        status, resp = send_message(
            access_token.strip(),
            phone_number_id.strip(),
            payload
        )

        results.append({
            "phone": phone,
            "status": status,
            "response": json.dumps(resp)[:200]
        })

        progress.progress(i / len(recipients))
        if delay:
            time.sleep(delay)

    st.success("✅ Broadcast completed")
    st.dataframe(pd.DataFrame(results), use_container_width=True)
