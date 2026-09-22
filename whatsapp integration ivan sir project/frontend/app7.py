import streamlit as st
import requests
import json

st.set_page_config(page_title="WhatsApp Image Template Sender", layout="centered")

st.title("📲 WhatsApp Cloud API - Image Header Template Sender")

with st.sidebar:
    st.header("🔐 Credentials")
    access_token = st.text_input("Permanent Access Token", type="password")
    phone_number_id = st.text_input("Phone Number ID", value="969440862917175")

recipient_number = st.text_input("Recipient (923xxxxxxxxx)")
template_name = st.text_input("Template Name", value="tutorial_web_federacion_v1")
language_code = st.text_input("Language Code", value="es")

image_url = st.text_input("Header Image Public URL")

if st.button("🚀 Send Template"):

    if not access_token or not recipient_number or not image_url:
        st.error("Missing required fields")
    else:
        url = f"https://graph.facebook.com/v19.0/{phone_number_id}/messages"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        payload = {
            "messaging_product": "whatsapp",
            "to": recipient_number,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code},
                "components": [
                    {
                        "type": "header",
                        "parameters": [
                            {
                                "type": "image",
                                "image": {
                                    "link": image_url
                                }
                            }
                        ]
                    }
                ]
            }
        }

        response = requests.post(url, headers=headers, json=payload)
        st.json(response.json())

        if response.status_code == 200:
            st.success("✅ Message Sent Successfully!")
        else:
            st.error("❌ Failed")
