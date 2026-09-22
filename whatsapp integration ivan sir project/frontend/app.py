import streamlit as st
import pandas as pd
import requests
import time

st.set_page_config(page_title="WhatsApp Bulk Sender (Excel Upload)", layout="centered")

st.title("WhatsApp Cloud API - Excel Bulk Sender")

# Sidebar Config
st.sidebar.header("WhatsApp Configuration")

access_token = st.sidebar.text_input("Access Token", type="password")
phone_number_id = st.sidebar.text_input("Phone Number ID")

st.divider()

st.subheader("Upload Excel File")

uploaded_file = st.file_uploader("Upload Excel or CSV file", type=["xlsx", "csv"])

message_text = st.text_area("Message Text")

send_button = st.button("Send Bulk Messages")


def send_whatsapp_message(token, phone_id, to, text):
    url = f"https://graph.facebook.com/v19.0/{phone_id}/messages"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {
            "body": text
        }
    }

    response = requests.post(url, headers=headers, json=payload)
    return response


def clean_number(num):
    num = str(num).strip()
    num = num.replace("+", "")
    num = num.replace(" ", "")
    return num


if send_button:

    if not access_token or not phone_number_id:
        st.error("Please enter Access Token and Phone Number ID.")
    elif not uploaded_file:
        st.error("Please upload a file.")
    elif not message_text:
        st.error("Please enter a message.")
    else:

        # Read file
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        if df.empty:
            st.error("File is empty.")
        else:
            st.success("File loaded successfully.")

            # Assume first column contains numbers
            numbers = df.iloc[:, 0].dropna().tolist()
            numbers = [clean_number(n) for n in numbers]

            total = len(numbers)
            success_count = 0
            fail_count = 0

            results = []

            progress_bar = st.progress(0)

            for index, number in enumerate(numbers):

                response = send_whatsapp_message(
                    access_token,
                    phone_number_id,
                    number,
                    message_text
                )

                if response.status_code == 200:
                    success_count += 1
                    results.append({"number": number, "status": "Sent"})
                else:
                    fail_count += 1
                    try:
                        error_data = response.json()
                    except:
                        error_data = response.text

                    results.append({
                        "number": number,
                        "status": "Failed",
                        "error": error_data
                    })

                progress_bar.progress((index + 1) / total)

                time.sleep(1)  # Rate limit protection

            st.subheader("Summary")
            st.success(f"Successfully Sent: {success_count}")
            st.error(f"Failed: {fail_count}")

            st.subheader("Detailed Report")
            st.json(results)