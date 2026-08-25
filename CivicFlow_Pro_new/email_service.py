import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ==========================================
# 📧 EMAIL CONFIGURATION
# ==========================================
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "gamertotex@gmail.com"    # <--- REPLACE WITH YOUR REAL GMAIL
SENDER_PASSWORD = "xoku xdyj skbq mbdk"  # <--- REPLACE WITH YOUR APP PASSWORD

def send_submission_email(recipient_email, tracking_id, department):
    """
    Sends the official HTML receipt to the citizen.
    (This function is called by a thread in app.py, so it runs in the background)
    """
    try:
        subject = f"Grievance Received - #{tracking_id}"
        
        # --- PROFESSIONAL HTML TEMPLATE ---
        html_body = f"""
        <html>
        <body style="font-family: 'Segoe UI', Arial, sans-serif; background-color: #f4f6f9; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
                
                <div style="background-color: #0b1e4c; padding: 30px 20px; text-align: center; color: white;">
                    <h1 style="margin: 0; font-size: 24px; text-transform: uppercase; letter-spacing: 2px;">CivicFlow</h1>
                    <p style="margin: 5px 0 0; font-size: 14px; opacity: 0.8;">Official Municipal Grievance Portal</p>
                </div>

                <div style="padding: 40px 30px;">
                    <h2 style="color: #333; margin-top: 0;">Grievance Registered</h2>
                    <p style="color: #666; line-height: 1.6;">
                        Dear Citizen,<br><br>
                        Your complaint has been successfully filed in our system. It has been automatically routed to the 
                        <strong>{department}</strong> for immediate review.
                    </p>

                    <div style="background-color: #f8f9fa; border-left: 5px solid #0d6efd; padding: 20px; margin: 20px 0; border-radius: 5px;">
                        <table style="width: 100%; border-collapse: collapse;">
                            <tr>
                                <td style="padding: 5px 0; color: #888; font-size: 12px; text-transform: uppercase;">Tracking ID</td>
                            </tr>
                            <tr>
                                <td style="padding-bottom: 15px; font-size: 20px; font-weight: bold; color: #333;">#{tracking_id}</td>
                            </tr>
                            <tr>
                                <td style="padding: 5px 0; color: #888; font-size: 12px; text-transform: uppercase;">Assigned Department</td>
                            </tr>
                            <tr>
                                <td style="font-size: 16px; font-weight: bold; color: #333;">{department}</td>
                            </tr>
                        </table>
                    </div>

                    <p style="color: #666; font-size: 14px;">
                        You can track the live status of this grievance or download your official receipt by logging into your dashboard.
                    </p>
                    
                    <div style="text-align: center; margin-top: 30px;">
                        <a href="http://127.0.0.1:5000/track" style="background-color: #0d6efd; color: white; padding: 12px 25px; text-decoration: none; border-radius: 50px; font-weight: bold; font-size: 14px;">Track Status</a>
                    </div>
                </div>

                <div style="background-color: #eee; padding: 20px; text-align: center; font-size: 11px; color: #999;">
                    &copy; 2026 CivicFlow Municipal System. All rights reserved.<br>
                    Automated System Email.
                </div>
            </div>
        </body>
        </html>
        """

        # --- SETUP MESSAGE ---
        msg = MIMEMultipart()
        msg['From'] = f"CivicFlow Portal <{SENDER_EMAIL}>"
        msg['To'] = recipient_email
        msg['Subject'] = subject
        msg.attach(MIMEText(html_body, 'html'))

        # --- SEND EMAIL (STARTTLS) ---
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()  # Secure the connection
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        print(f"✅ Email sent successfully to {recipient_email}")

    except Exception as e:
        print(f"❌ Email Failed: {e}")