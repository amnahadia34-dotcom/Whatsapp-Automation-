import streamlit as st
import pandas as pd
import requests
import time

st.set_page_config(page_title="WhatsApp Enterprise Broadcast", layout="wide")

st.title("WhatsApp Enterprise Broadcast System")

# ==============================
# SIDEBAR CONFIGURATION
# ==============================

st.sidebar.header("Meta Configuration")

access_token = st.sidebar.text_input("Access Token", type="password")
phone_number_id = st.sidebar.text_input("Phone Number ID")
waba_id = st.sidebar.text_input("WABA ID")

# ==============================
# FETCH APPROVED TEMPLATES
# ==============================

def fetch_templates(token, waba):
    url = f"https://graph.facebook.com/v19.0/{waba}/message_templates"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = response.json().get("data", [])
        approved = [t for t in data if t["status"] == "APPROVED"]
        return approved
    return []

templates = []
if access_token and waba_id:
    templates = fetch_templates(access_token, waba_id)

template_names = [t["name"] for t in templates]

# ==============================
# TEMPLATE SELECTION
# ==============================

st.subheader("Template Selection")

if template_names:
    template_name = st.selectbox("Select Approved Template", template_names)
    selected_template = next((t for t in templates if t["name"] == template_name), None)
else:
    template_name = st.text_input("Template Name")
    selected_template = None

language_code = st.text_input("Language Code", value="en_US")

# ==============================
# CONTACT FILE UPLOAD
# ==============================

st.subheader("Upload Contacts File")

uploaded_file = st.file_uploader("Upload Excel or CSV", type=["xlsx", "csv"])

df = None

if uploaded_file:
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    st.success(f"{len(df)} contacts loaded successfully.")

# ==============================
# PREVIEW SECTION
# ==============================

st.subheader("Live Preview")

if template_name and df is not None:
    st.info(f"""
Template: {template_name}  
Language: {language_code}  
Total Recipients: {len(df)}
    """)

    if selected_template:
        st.write("Template Structure:")
        st.json(selected_template.get("components", []))

# ==============================
# CONFIRMATION CHECK
# ==============================

st.subheader("Broadcast Confirmation")

confirm_send = st.checkbox("I confirm this broadcast is correct and ready to send.")

send_button = st.button("Send Broadcast")

# ==============================
# SEND FUNCTION
# ==============================

def send_template_message(token, phone_id, number, template, lang, variables=None):

    url = f"https://graph.facebook.com/v19.0/{phone_id}/messages"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": number,
        "type": "template",
        "template": {
            "name": template,
            "language": {"code": lang}
        }
    }

    if variables:
        payload["template"]["components"] = [
            {
                "type": "body",
                "parameters": [{"type": "text", "text": str(v)} for v in variables]
            }
        ]

    return requests.post(url, headers=headers, json=payload)

# ==============================
# BROADCAST PROCESS
# ==============================

if send_button:

    if not access_token or not phone_number_id:
        st.error("Access Token and Phone Number ID are required.")
    elif df is None:
        st.error("Please upload contact file.")
    elif not confirm_send:
        st.warning("Please confirm before sending broadcast.")
    else:

        numbers = df.iloc[:, 0].astype(str).tolist()
        total = len(numbers)

        success = 0
        failed = 0
        results = []

        progress_bar = st.progress(0)

        for i, number in enumerate(numbers):

            variables = None
            if df.shape[1] > 1:
                variables = df.iloc[i, 1:].tolist()

            response = send_template_message(
                access_token,
                phone_number_id,
                number,
                template_name,
                language_code,
                variables
            )

            if response.status_code == 200:
                success += 1
                results.append({"number": number, "status": "Sent"})
            else:
                failed += 1
                results.append({
                    "number": number,
                    "status": "Failed",
                    "error": response.text
                })

            progress_bar.progress((i + 1) / total)
            time.sleep(1)

        st.subheader("Broadcast Summary")
        st.success(f"Successfully Sent: {success}")
        st.error(f"Failed: {failed}")

        st.subheader("Detailed Report")
        st.json(results)