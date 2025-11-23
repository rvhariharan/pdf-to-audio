from flask import Flask, render_template, request, send_file, redirect, url_for, jsonify
import os
from gtts import gTTS
import time
from PyPDF2 import PdfReader
from werkzeug.utils import secure_filename 

app = Flask(__name__, static_folder="static")

# Desktop App Path
DESKTOP_APP_PATH = os.path.join("download", "app.exe")

# Folder Config
UPLOAD_FOLDER = 'uploads'
AUDIO_FOLDER = 'static/audio'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(AUDIO_FOLDER, exist_ok=True)

# --- 1. PDF TEXT EXTRACTION ---
def extract_text_from_pdf(pdf_path):
    text = ""
    try:
        reader = PdfReader(pdf_path)
        for page in reader.pages:
            text += page.extract_text() or ""
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return None
    return text.strip()

# --- 2. CONVERSION LOGIC (Using gTTS for Reliability) ---
def convert_text_to_audio(text, output_file, voice_type="Male"):
    try:
        if not text or len(text.strip()) == 0:
            return False

        # Google TTS Trick for Voices:
        # gTTS doesn't have "Male/Female" switch, but we can change accents (TLD).
        # 'us' = US English (Standard Female-ish)
        # 'co.in' = Indian English (Often sounds slightly different/Male-ish in some versions or just distinct)
        # 'co.uk' = British English
        
        if voice_type == "Male":
            # Using Indian accent or UK to simulate a different tone
            tld_option = 'co.in' 
        else:
            # Standard US Female voice
            tld_option = 'us'

        # Create gTTS object
        tts = gTTS(text=text, lang='en', tld=tld_option, slow=False)
        
        # Save file
        tts.save(output_file)
            
        return True
    except Exception as e:
        print(f"CRITICAL ERROR converting text to audio: {e}")
        return False

# --- 3. ROUTES ---
@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            return jsonify({"error": "No file part"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400

        voice_type = request.form.get('voice', 'Male')

        if file and file.filename.endswith('.pdf'):
            filename = secure_filename(file.filename)
            pdf_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(pdf_path)

            # Step 1: Extract Text
            text = extract_text_from_pdf(pdf_path)
            
            # Step 2: Validation
            if not text or len(text.strip()) == 0:
                return jsonify({"error": "Empty PDF or Scanned Image detected. Cannot read text."}), 400

            # Step 3: Generate Filename
            audio_filename = f"{os.path.splitext(filename)[0]}_{int(time.time())}.mp3"
            audio_path = os.path.join(AUDIO_FOLDER, audio_filename)

            # Step 4: Convert
            success = convert_text_to_audio(text, audio_path, voice_type)
            
            if not success:
                return jsonify({"error": "Server Error: Could not convert text."}), 500

            # Step 5: Send Response
            return jsonify({
                "audio_url": url_for('static', filename=f"audio/{audio_filename}"),
                "filename": audio_filename
            })

    return render_template('index.html')

@app.route('/download/<filename>')
def download_audio(filename):
    audio_path = os.path.join(AUDIO_FOLDER, filename)
    if os.path.exists(audio_path):
        return send_file(audio_path, as_attachment=True)
    return "File not found", 404

@app.route('/delete/<filename>', methods=['POST'])
def delete_audio(filename):
    try:
        audio_path = os.path.join(AUDIO_FOLDER, filename)
        if os.path.exists(audio_path):
            os.remove(audio_path)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/download_app')
def download_app():
    if os.path.exists(DESKTOP_APP_PATH):
        return send_file(DESKTOP_APP_PATH, as_attachment=True)
    else:
        return "App not found on server", 404

if __name__ == '__main__':
    app.run(debug=True)