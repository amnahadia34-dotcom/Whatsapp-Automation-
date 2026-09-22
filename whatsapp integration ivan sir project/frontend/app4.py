import streamlit as st
import pandas as pd
import requests
import time
import re

st.set_page_config(page_title="WhatsApp Template Bulk Sender", layout="centered")
st.title("WhatsApp Cloud API - Template Bulk Sender")

# ===============================
# SESSION LOCK
# ===============================
if "sending" not in st.session_state:
    st.session_state.sending = False

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
    "Header Type",
    ["NONE", "IMAGE", "VIDEO"]
)

media_url = ""
if header_type in ["IMAGE", "VIDEO"]:
    media_url = st.text_input("Public HTTPS Media URL")

uploaded_file = st.file_uploader(
    "Upload Excel/CSV (First column = Numbers)",
    type=["xlsx", "csv"]
)

send_button = st.button("Send Template Broadcast")

# ===============================
# CLEAN & VALIDATE NUMBER
# ===============================
def clean_number(number):
    number = re.sub(r"\D", "", str(number)).strip()

    if number.startswith("0"):
        number = "92" + number[1:]

    if number.startswith("+"):
        number = number.replace("+", "")

    # Pakistan validation (92XXXXXXXXXX = 12 digits)
    if not number.startswith("92") or len(number) != 12:
        return None

    return number


# ===============================
# SEND FUNCTION WITH RETRY
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
        template_payload["components"] = [{
            "type": "header",
            "parameters": [{
                "type": "image",
                "image": {"link": media_url}
            }]
        }]

    elif header_type == "VIDEO":
        template_payload["components"] = [{
            "type": "header",
            "parameters": [{
                "type": "video",
                "video": {"link": media_url}
            }]
        }]

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "template",
        "template": template_payload
    }

    for attempt in range(3):  # 3 attempts retry
        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=20
            )

            try:
                data = response.json()
            except:
                data = response.text

            # True success only if message ID exists
            if response.status_code == 200 and isinstance(data, dict) and "messages" in data:
                return True, data

        except Exception as e:
            data = str(e)

        time.sleep(3)

    return False, data


# ===============================
# BROADCAST LOGIC
# ===============================
if send_button and not st.session_state.sending:

    st.session_state.sending = True

    if not access_token or not phone_number_id:
        st.error("Enter Access Token and Phone Number ID.")

    elif not template_name:
        st.error("Enter Template Name.")

    elif header_type in ["IMAGE", "VIDEO"] and not media_url:
        st.error("Media URL required.")

    elif not uploaded_file:
        st.error("Upload numbers file.")

    else:

        # Read file
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        raw_numbers = df.iloc[:, 0].dropna().tolist()

        numbers = [clean_number(n) for n in raw_numbers]
        numbers = [n for n in numbers if n is not None]
        numbers = list(dict.fromkeys(numbers))  # safe duplicate removal

        st.write("Final Clean Numbers:", numbers)

        success = 0
        failed = 0
        results = []

        progress = st.progress(0)

        for i, number in enumerate(numbers):

            sent, response_data = send_template_message(
                access_token,
                phone_number_id,
                number,
                template_name,
                header_type,
                media_url
            )

            if sent:
                success += 1
                results.append({"number": number, "status": "Sent"})
            else:
                failed += 1
                results.append({
                    "number": number,
                    "status": "Failed",
                    "error": response_data
                })

            progress.progress((i + 1) / len(numbers))
            time.sleep(3)

        st.subheader("Broadcast Summary")
        st.success(f"Sent Successfully: {success}")
        st.error(f"Failed: {failed}")

        st.subheader("Detailed Report")
        st.json(results)

    st.session_state.sending = False