from flask import Flask, render_template, request, send_file, redirect, url_for, jsonify
import os
import edge_tts
import asyncio
import time
from PyPDF2 import PdfReader
from werkzeug.utils import secure_filename 

app = Flask(__name__, static_folder="static")

DESKTOP_APP_PATH = os.path.join("download", "app.exe")
UPLOAD_FOLDER = 'uploads'
AUDIO_FOLDER = 'static/audio'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(AUDIO_FOLDER, exist_ok=True)

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

async def generate_audio_edge(text, output_file, voice_short_name):
    communicate = edge_tts.Communicate(text, voice_short_name)
    await communicate.save(output_file)

def convert_text_to_audio(text, output_file, voice_type="Male"):
    try:
        # Male = Guy, Female = Aria (Microsoft Voices)
        if voice_type == "Male":
            voice_id = "en-US-GuyNeural"
        else:
            voice_id = "en-US-AriaNeural"
            
        asyncio.run(generate_audio_edge(text, output_file, voice_id))
        return True
    except Exception as e:
        print(f"Error converting text to audio: {e}")
        return False

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

            text = extract_text_from_pdf(pdf_path)
            if not text or len(text.strip()) == 0:
                return jsonify({"error": "Empty PDF or Scanned Image. Cannot read text."}), 400

            # Timestamp add panrom for unique filename
            audio_filename = f"{os.path.splitext(filename)[0]}_{int(time.time())}.mp3"
            audio_path = os.path.join(AUDIO_FOLDER, audio_filename)

            success = convert_text_to_audio(text, audio_path, voice_type)
            if not success:
                return jsonify({"error": "Failed to convert text to audio."}), 500

            # Important: JSON response sends the URL back to JavaScript
            return jsonify({
                "audio_url": url_for('static', filename=f"audio/{audio_filename}"),
                "filename": audio_filename
            })

    # Note: Inga 'audio_files' list anuppala. So page load aagum bothu empty ah irukum.
    return render_template('index.html')

@app.route('/download/<filename>')
def download_audio(filename):
    audio_path = os.path.join(AUDIO_FOLDER, filename)
    if os.path.exists(audio_path):
        return send_file(audio_path, as_attachment=True)
    return "File not found", 404

# Delete route theva padathu (user refresh panna file poidum visually), 
# but backend safety kaga vechukalam.
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
        return "App not found", 404

if __name__ == '__main__':
    app.run(debug=True)