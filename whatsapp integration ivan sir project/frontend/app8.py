import streamlit as st
import pandas as pd
import requests
import time
import re

st.set_page_config(page_title="WhatsApp Template Bulk Sender", layout="centered")
st.title("WhatsApp Cloud API - Template Bulk Sender")

# ===============================
# SIDEBAR CONFIG
# ===============================
st.sidebar.header("WhatsApp Configuration")

access_token = st.sidebar.text_input("Access Token", type="password")
phone_number_id = st.sidebar.text_input("Phone Number ID")

st.divider()

# ===============================
# TEMPLATE CONFIG
# ===============================
st.subheader("Template Configuration")

template_name = st.text_input("Template Name (Exact from Meta)")
language_code = "es"

header_type = st.selectbox(
    "Header Type (Select according to template)",
    ["NONE", "IMAGE", "VIDEO"]
)

media_url = ""
if header_type in ["IMAGE", "VIDEO"]:
    media_url = st.text_input(
        "Public HTTPS Media URL (.jpg/.png for IMAGE, .mp4 for VIDEO)"
    )

uploaded_file = st.file_uploader(
    "Upload Excel/CSV (Numbers in any column)",
    type=["xlsx", "csv"]
)

send_button = st.button("Send Template Broadcast")

# ===============================
# CLEAN NUMBER FUNCTION
# ===============================
def clean_number(number):
    number = re.sub(r"\D", "", str(number))

    if number.startswith("0"):
        number = "92" + number[1:]

    if number.startswith("92") and len(number) >= 12:
        return number

    return None


# ===============================
# SEND FUNCTION
# ===============================
def send_template_message(token, phone_id, to, template, header_type, media_url):

    url = f"https://graph.facebook.com/v19.0/{phone_id}/messages"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    template_payload = {
        "name": template.strip(),
        "language": {"code": language_code}
    }

    if header_type == "IMAGE":
        template_payload["components"] = [
            {
                "type": "header",
                "parameters": [
                    {
                        "type": "image",
                        "image": {"link": media_url}
                    }
                ]
            }
        ]

    elif header_type == "VIDEO":
        template_payload["components"] = [
            {
                "type": "header",
                "parameters": [
                    {
                        "type": "video",
                        "video": {"link": media_url}
                    }
                ]
            }
        ]

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "template",
        "template": template_payload
    }

    response = requests.post(url, headers=headers, json=payload)
    return response


# ===============================
# BROADCAST LOGIC
# ===============================
if send_button:

    if not access_token or not phone_number_id:
        st.error("Enter Access Token and Phone Number ID.")

    elif not template_name:
        st.error("Enter Template Name.")

    elif header_type in ["IMAGE", "VIDEO"] and not media_url:
        st.error("Media URL required for selected header type.")

    elif not uploaded_file:
        st.error("Upload numbers file.")

    else:

        # Read file
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        # Extract numbers from ALL columns
        raw_numbers = []
        for col in df.columns:
            raw_numbers.extend(df[col].dropna().tolist())

        # Clean and validate
        cleaned_numbers = []
        for n in raw_numbers:
            num = clean_number(n)
            if num:
                cleaned_numbers.append(num)

        # Remove duplicates
        numbers = list(set(cleaned_numbers))

        if not numbers:
            st.error("No valid numbers found in file.")
            st.stop()

        st.info(f"Total Valid Unique Numbers Found: {len(numbers)}")

        success = 0
        failed = 0
        results = []

        progress = st.progress(0)

        for i, number in enumerate(numbers):

            response = send_template_message(
                access_token,
                phone_number_id,
                number,
                template_name,
                header_type,
                media_url
            )

            try:
                data = response.json()
            except:
                data = response.text

            if response.status_code == 200:
                success += 1
                results.append({"number": number, "status": "Sent"})
            else:
                failed += 1
                results.append({
                    "number": number,
                    "status": "Failed",
                    "error": data
                })

            progress.progress((i + 1) / len(numbers))
            time.sleep(1)

        st.subheader("Broadcast Summary")
        st.success(f"Sent Successfully: {success}")
        st.error(f"Failed: {failed}")

        st.subheader("Detailed Report")
        st.json(results)