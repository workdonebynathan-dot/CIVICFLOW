from xhtml2pdf import pisa
from io import BytesIO

html_content = """
<!DOCTYPE html>
<html>
<head>
    <style>
        @page { size: A4; margin: 1cm; }
        body { font-family: 'Helvetica', sans-serif; color: #333; font-size: 11px; }
    </style>
</head>
<body>
    <div class="logo">🏛️ CivicFlow Municipal Report</div>
</body>
</html>
"""

pdf_file = BytesIO()
pisa_status = pisa.CreatePDF(html_content, dest=pdf_file)
if pisa_status.err:
    print(f"Error: {pisa_status.err}")
else:
    print("Success")
