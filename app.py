from flask import Flask, request, send_file, render_template_string
import os
from werkzeug.utils import secure_filename
from redact import PiiRedactor

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize the redactor globally so it's loaded once
redactor = PiiRedactor()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PII Redaction Tool</title>
    <style>
        body { font-family: sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; text-align: center; }
        .upload-btn { background-color: #4CAF50; color: white; padding: 10px 20px; border: none; cursor: pointer; font-size: 16px; border-radius: 5px; }
        .upload-btn:hover { background-color: #45a049; }
        input[type="file"] { margin-bottom: 20px; }
    </style>
</head>
<body>
    <h1>PII Redaction Tool</h1>
    <p>Upload a .docx file to securely redact PII (Personally Identifiable Information).</p>
    <form action="/redact" method="post" enctype="multipart/form-data">
        <input type="file" name="file" accept=".docx" required>
        <br><br>
        <input type="submit" value="Upload & Redact" class="upload-btn">
    </form>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/redact', methods=['POST'])
def redact_file():
    if 'file' not in request.files:
        return "No file part", 400
    file = request.files['file']
    if file.filename == '':
        return "No selected file", 400
        
    if file and file.filename.endswith('.docx'):
        filename = secure_filename(file.filename)
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(input_path)
        
        output_filename = f"redacted_{filename}"
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)
        
        # Process the file
        try:
            redactor.process_docx(input_path, output_path)
            return send_file(output_path, as_attachment=True)
        except Exception as e:
            return f"An error occurred: {str(e)}", 500
            
    return "Invalid file type. Please upload a .docx file", 400

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
