import os
import jwt
import requests
import time
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

class PDFGeneratorClient:
    def __init__(self):
        self.key = os.getenv("PDF_KEY")
        self.secret = os.getenv("PDF_SECRET")
        self.workspace = os.getenv("PDF_WORKSPACE")
        self.template_id ="1592650"
        # Ensure we are using v3 since that is what worked
        self.base_url = "https://us1.pdfgeneratorapi.com/api/v3"

        if not all([self.key, self.secret, self.workspace, self.template_id]):
            st.error("🚨 Configuration Error: Missing API credentials in .env file")

    def _get_jwt(self):
        payload = {
            "iss": self.key,
            "sub": self.workspace,
            "exp": int(time.time()) + 60
        }
        return jwt.encode(payload, self.secret, algorithm="HS256")

    def generate_pdf(self, data):
        try:
            token = self._get_jwt()
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            body = {
                "responseFormat": "pdf",
                "data": data
            }
            
            # v3 Endpoint Call
            response = requests.post(
                f"{self.base_url}/templates/{self.template_id}/output",
                headers=headers,
                json=body
            )
            
            if response.status_code == 200:
                # SUCCESS! Return the raw bytes directly.
                # Do NOT use response.json() here.
                return response.content
            else:
                st.error(f"API Error ({response.status_code}): {response.text}")
                return None
                
        except Exception as e:
            st.error(f"Connection Failed: {str(e)}")
            return None