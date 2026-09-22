import streamlit as st
import pandas as pd
import requests
import time
import re
import json

st.set_page_config(page_title="WhatsApp Template Bulk Sender", layout="centered")

st.title("WhatsApp Cloud API - Template Bulk Sender")

# ===============================
# SIDEBAR CONFIGURATION
# ===============================
st.sidebar.header("WhatsApp Configuration")

access_token = st.sidebar.text_input("Access Token", type="password")
phone_number_id = st.sidebar.text_input("Phone Number ID")

st.divider()

# ===============================
# TEMPLATE CONFIGURATION
# ===============================
st.subheader("Template Configuration")

template_name = st.text_input(
    "Template Name (Approved in Meta)",
    value="banner_federacion_v1"
)

# HARD CODED LANGUAGE (VERY IMPORTANT)
language_code = "es_ES"

st.info(f"Using Language Code: {language_code}")

uploaded_file = st.file_uploader(
    "Upload Excel/CSV (First column = Numbers)",
    type=["xlsx", "csv"]
)

send_button = st.button("Send Template Broadcast")


# ===============================
# NUMBER CLEANER
# ===============================
def clean_number(number):
    number = re.sub(r"\D", "", str(number))

    if number.startswith("0"):
        number = "92" + number[1:]

    return number


# ===============================
# SEND TEMPLATE FUNCTION
# ===============================
def send_template_message(token, phone_id, to, template):

    url = f"https://graph.facebook.com/v19.0/{phone_id}/messages"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "template",
        "template": {
            "name": template.strip(),
            "language": {
                "code": language_code
            }
        }
    }

    response = requests.post(url, headers=headers, json=payload)
    return response, payload


# ===============================
# BROADCAST LOGIC
# ===============================
if send_button:

    if not access_token or not phone_number_id:
        st.error("⚠ Please enter Access Token and Phone Number ID.")
        
    elif not template_name:
        st.error("⚠ Please enter Template Name.")
        
    elif not uploaded_file:
        st.error("⚠ Please upload numbers file.")
        
    else:

        # READ FILE
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        raw_numbers = df.iloc[:, 0].dropna().tolist()
        numbers = [clean_number(n) for n in raw_numbers]

        total = len(numbers)
        success = 0
        failed = 0
        results = []

        progress = st.progress(0)

        for i, number in enumerate(numbers):

            response, payload_sent = send_template_message(
                access_token,
                phone_number_id,
                number,
                template_name
            )

            try:
                response_data = response.json()
            except:
                response_data = response.text

            if response.status_code == 200:
                success += 1
                results.append({
                    "number": number,
                    "status": "Sent",
                    "response": response_data
                })
            else:
                failed += 1
                results.append({
                    "number": number,
                    "status": "Failed",
                    "error": response_data,
                    "payload_sent": payload_sent
                })

            progress.progress((i + 1) / total)
            time.sleep(1)

        # ===============================
        # RESULTS
        # ===============================
        st.subheader("Broadcast Summary")
        st.success(f"Sent Successfully: {success}")
        st.error(f"Failed: {failed}")

        st.subheader("Detailed Report")
        st.json(results)