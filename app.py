#Download APIs to make program work
#pip install Flask,pip install Pillow, pip install google-genai, pip install nba_api, pip install pandas
from flask import Flask, request, jsonify, render_template, send_from_directory
import os
import uuid
from player_backend import get_player_info

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    sport = request.form.get('sport')
    file = request.files.get('player_image')

    if not file or not allowed_file(file.filename):
        return jsonify({'error': 'Invalid or missing file'}), 400

    # Create a unique file name
    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)

    # Call your friend's logic to build the paragraph
    player_info = get_player_info(file_path, sport)

    return jsonify({
        'sport': sport,
        'image_url': f'/uploads/{filename}',
        'player_info': player_info
    })

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)
