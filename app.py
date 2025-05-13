from flask import Flask, request, render_template, send_file
from drive_utils import get_drive_service, list_images_from_folder
from face_matcher import load_face_encodings_from_images, match_face
import os
import requests
import zipfile
import io

app = Flask(__name__)
DOWNLOAD_DIR = 'downloaded_images'
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

matched_files = []  # Store matched file paths

@app.route('/', methods=['GET', 'POST'])
def index():
    global matched_files
    if request.method == 'POST':
        folder_url = request.form['drive_url']
        input_image = request.files['face_image']

        # Extract folder ID from Google Drive link
        try:
            folder_id = folder_url.split('/folders/')[1].split('/')[0]
        except IndexError:
            return "Invalid Drive folder URL. Please make sure it follows the correct format."

        # Save the uploaded face image
        input_path = os.path.join(DOWNLOAD_DIR, 'input.jpg')
        input_image.save(input_path)

        # Initialize Drive API
        try:
            service = get_drive_service()
        except Exception as e:
            return f"Error initializing Drive API: {e}"

        # Get files from Drive folder
        try:
            files = list_images_from_folder(service, folder_id)
        except Exception as e:
            return f"Drive access error: {e}"

        # Download images
        image_paths = []
        for f in files:
            file_id = f['id']
            file_name = f['name']
            file_path = os.path.join(DOWNLOAD_DIR, file_name)
            try:
                download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
                with open(file_path, 'wb') as img_file:
                    img_file.write(requests.get(download_url).content)
                image_paths.append(file_path)
            except Exception as e:
                print(f"Failed to download {file_name}: {e}")

        # Face recognition
        known_faces = load_face_encodings_from_images(image_paths)
        matches = match_face(input_path, known_faces)

        matched_files = [m[0] for m in matches]  # Save for ZIP
        return render_template('results.html', matches=matches)

    return render_template('index.html')


@app.route('/download-zip')
def download_zip():
    global matched_files
    zip_stream = io.BytesIO()
    with zipfile.ZipFile(zip_stream, 'w') as zf:
        for file_path in matched_files:
            filename = os.path.basename(file_path)
            zf.write(file_path, arcname=filename)
    zip_stream.seek(0)
    return send_file(zip_stream, mimetype='application/zip', as_attachment=True, download_name='matched_images.zip')


if __name__ == '__main__':
    app.run(debug=True)
