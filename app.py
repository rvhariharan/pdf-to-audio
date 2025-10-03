from flask import Flask, render_template, request, send_file, redirect, url_for, jsonify
import os
import pyttsx3
import time
from PyPDF2 import PdfReader
from werkzeug.utils import secure_filename 

app = Flask(__name__, static_folder="static")

# Add this line at the top with other constants
DESKTOP_APP_PATH = os.path.join("download", "app.exe")
# Folder paths-a define
UPLOAD_FOLDER = 'uploads'
AUDIO_FOLDER = 'static/audio'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(AUDIO_FOLDER, exist_ok=True)

# Text-to-Speech engine-a initialize 
try:
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')
    AVAILABLE_VOICES = {
        "Male": [voice.id for voice in voices if "male" in voice.name.lower()] or [voices[0].id],
        "Female": [voice.id for voice in voices if "female" in voice.name.lower()] or [voices[-1].id]
    }
except Exception as e:
    print(f"Could not initialize pyttsx3 engine: {e}")
    voices = []
    AVAILABLE_VOICES = {"Male": [None], "Female": [None]}


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

def convert_text_to_audio(text, output_file, speed=1.0, voice_type="Male"):
    try:
        engine.setProperty('rate', int(200 * speed))
        voice_id = AVAILABLE_VOICES.get(voice_type, [voices[0].id if voices else None])[0]
        if voice_id:
            engine.setProperty('voice', voice_id)
        engine.save_to_file(text, output_file)
        engine.runAndWait()
        return True
    except Exception as e:
        print(f"Error converting text to audio: {e}")
        return False

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # File checking process 
        if 'file' not in request.files:
            return jsonify({"error": "No file part"}), 400
        
        file = request.files['file']
        
        # File submit without select
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400

        voice_type = request.form.get('voice', 'Male')
        speed = float(request.form.get('speed', 1.0))

        if file and file.filename.endswith('.pdf'):
            # secure File name
            filename = secure_filename(file.filename)
            pdf_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(pdf_path)

            text = extract_text_from_pdf(pdf_path)
            if not text:
                return jsonify({"error": "Could not extract text from PDF."}), 400

            # give unick name on audio file
            audio_filename = f"{os.path.splitext(filename)[0]}_{int(time.time())}.mp3"
            audio_path = os.path.join(AUDIO_FOLDER, audio_filename)

            success = convert_text_to_audio(text, audio_path, speed, voice_type)
            if not success:
                return jsonify({"error": "Failed to convert text to audio."}), 500

            # JavaScript audio file's URL sent to JSON format.
            return jsonify({"audio_url": url_for('static', filename=f"audio/{audio_filename}")})

    audio_files = sorted(
        [f for f in os.listdir(AUDIO_FOLDER) if f.endswith('.mp3')],
        key=lambda f: os.path.getmtime(os.path.join(AUDIO_FOLDER, f)),
        reverse=True
    )
    return render_template('index.html', audio_files=audio_files)

@app.route('/download/<filename>')
def download_audio(filename):
    audio_path = os.path.join(AUDIO_FOLDER, filename)
    return send_file(audio_path, as_attachment=True)

@app.route('/delete/<filename>', methods=['POST'])
def delete_audio(filename):
    try:
        audio_path = os.path.join(AUDIO_FOLDER, filename)
        if os.path.exists(audio_path):
            os.remove(audio_path)
        return redirect(url_for('upload_file'))
    except Exception as e:
        print(f"Error deleting file: {e}")
        return redirect(url_for('upload_file'))
    
@app.route('/download_app')
def download_app():
    return send_file(DESKTOP_APP_PATH, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)