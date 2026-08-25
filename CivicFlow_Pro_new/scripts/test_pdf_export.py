import app
from app import app as flask_app
from xhtml2pdf import pisa
from io import BytesIO
import datetime
from flask import render_template

with flask_app.app_context():
    # Mock data
    complaints = [
        {"tracking_id": "123", "created_at": "27-06-2026", "department": "Water", "urgency": "High", "status": "Pending", "complaint": "Pipe broken"}
    ]
    html_content = render_template("report_pdf.html", complaints=complaints, date=datetime.date.today().strftime("%d-%B-%Y"))
    pdf_file = BytesIO()
    pisa_status = pisa.CreatePDF(html_content, dest=pdf_file)
    if pisa_status.err:
        print(f"Error: {pisa_status.err}")
    else:
        print("Success")
