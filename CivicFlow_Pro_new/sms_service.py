from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

# --- TWILIO CONFIGURATION (Get from Dashboard) ---
ACCOUNT_SID = "9MTL85PJGB49NX3YSW1B1ZBQ"  # <--- YOUR SID
AUTH_TOKEN = "fbb1a0becfe959905bd46bb28a25c6c3"  # <--- YOUR TOKEN
TWILIO_PHONE = "+919048805842"                   # <--- YOUR TWILIO NUMBER

def send_sms_alert(user_phone, tracking_id, status):
    """
    Sends a real SMS alert to the citizen.
    """
    try:
        # Basic check to ensure phone number has country code (India example)
        if not user_phone.startswith('+'):
            user_phone = "+91" + user_phone.strip()

        client = Client(ACCOUNT_SID, AUTH_TOKEN)

        msg_body = f"CivicFlow: Complaint #{tracking_id} Registered. Status: {status}. Track at portal."

        message = client.messages.create(
            body=msg_body,
            from_=TWILIO_PHONE,
            to=user_phone
        )
        print(f"✅ SMS Sent Successfully! SID: {message.sid}")

    except Exception as e:
        print(f"❌ SMS Failed: {e}")
        print("Tip: If using a Trial Account, did you verify the destination number on Twilio?")