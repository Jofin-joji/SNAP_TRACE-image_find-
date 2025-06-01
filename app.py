# app.py
from flask import Flask, render_template, request, jsonify, send_from_directory, send_file, url_for
import face_recognition
import os
import json
import cv2 # OpenCV for image handling
import numpy as np
import base64
import io # For handling image bytes
from werkzeug.utils import secure_filename # For secure file uploads
import time # For unique filenames (if needed)
import traceback # For detailed error logging

app = Flask(__name__)

# --- Configuration ---
EVENT_PHOTOS_DIR = "event_photos"
ENCODINGS_FILE = "known_faces_encodings.json"
MAX_PREPROCESSING_SIZE = 1024
FACE_DETECTION_MODEL = "hog"
COMPARISON_TOLERANCE = 0.58
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

# --- Ensure directories exist ---
if not os.path.exists(EVENT_PHOTOS_DIR):
    os.makedirs(EVENT_PHOTOS_DIR)
    print(f"Created directory: {EVENT_PHOTOS_DIR}")

# --- Global variable for loaded encodings ---
KNOWN_ENCODINGS_DATA = []

# --- Helper Functions ---
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Image Utility Functions ---
def resize_image_if_needed(image_cv2, max_size):
    h, w = image_cv2.shape[:2]
    if max(h, w) > max_size:
        if h > w: new_h, new_w = max_size, int(w * (max_size / h))
        else: new_w, new_h = max_size, int(h * (max_size / w))
        # print(f"Resizing from {w}x{h} to {new_w}x{new_h}")
        return cv2.resize(image_cv2, (new_w, new_h), interpolation=cv2.INTER_AREA)
    return image_cv2

def image_to_rgb(image_path_or_bytes, for_preprocessing=False):
    print(f"image_to_rgb: Called. for_preprocessing={for_preprocessing}")
    try:
        img_bgr = None # Initialize
        if isinstance(image_path_or_bytes, str):
            print(f"image_to_rgb: Loading from path: {image_path_or_bytes}")
            img_bgr = cv2.imread(image_path_or_bytes)
        elif isinstance(image_path_or_bytes, bytes): # Explicitly check for bytes
            print(f"image_to_rgb: Decoding from bytes, length: {len(image_path_or_bytes)}")
            nparr = np.frombuffer(image_path_or_bytes, np.uint8)
            img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img_bgr is None:
                 print("image_to_rgb: cv2.imdecode returned None from bytes.")
        else:
            print(f"image_to_rgb: Received unsupported type for image_path_or_bytes: {type(image_path_or_bytes)}")
            return None
        
        if img_bgr is None:
            print(f"image_to_rgb: img_bgr is None after attempting to load/decode.") # Critical print
            return None
        
        print(f"image_to_rgb: Successfully loaded/decoded image. Shape: {img_bgr.shape}")

        if for_preprocessing:
            print("image_to_rgb: Applying preprocessing resize.")
            img_bgr = resize_image_if_needed(img_bgr, MAX_PREPROCESSING_SIZE)
            print(f"image_to_rgb: Shape after potential resize: {img_bgr.shape}")

        
        rgb_img = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        print("image_to_rgb: Successfully converted to RGB.")
        return rgb_img
    except Exception as e:
        print(f"CRITICAL ERROR in image_to_rgb: {e}") # Catch any unexpected exception
        traceback.print_exc() # Print full traceback for the exception within image_to_rgb
        return None

# --- NEW: Optimized Preprocessing for Specific Files ---
def process_specific_new_photos(new_photo_paths):
    if not new_photo_paths:
        return "No new photos provided for specific processing."
    all_encodings_data = []
    if os.path.exists(ENCODINGS_FILE):
        try:
            with open(ENCODINGS_FILE, 'r') as f: all_encodings_data = json.load(f)
        except json.JSONDecodeError:
            print(f"Warning: {ENCODINGS_FILE} corrupted. Starting fresh for these files.")
            all_encodings_data = []
    existing_paths_in_json = {item['image_path'] for item in all_encodings_data}
    processed_count = 0
    for image_path in new_photo_paths:
        if image_path in existing_paths_in_json:
            print(f"Skipping {image_path} as it's already in encodings (specific processing).")
            continue
        print(f"Specifically processing: {image_path}...")
        image_rgb = image_to_rgb(image_path, for_preprocessing=True)
        if image_rgb is None:
            print(f"Failed to load {image_path} for specific processing. Skipping.")
            all_encodings_data.append({"image_path": image_path, "encodings": [], "error": "load_failed_specific"})
            continue
        face_locations = face_recognition.face_locations(image_rgb, model=FACE_DETECTION_MODEL)
        current_image_encodings = face_recognition.face_encodings(image_rgb, face_locations)
        serializable_encodings = [enc.tolist() for enc in current_image_encodings]
        all_encodings_data.append({"image_path": image_path, "encodings": serializable_encodings})
        if serializable_encodings: print(f"Found {len(serializable_encodings)} face(s) in new photo {os.path.basename(image_path)}")
        else: print(f"No faces found in new photo {os.path.basename(image_path)}")
        processed_count += 1
    if processed_count > 0 or not os.path.exists(ENCODINGS_FILE):
        try:
            with open(ENCODINGS_FILE, 'w') as f: json.dump(all_encodings_data, f, indent=2)
            message = f"Specifically processed {processed_count} new photo(s). Encodings updated."
            print(message); return message
        except IOError as e: message = f"Error writing encodings (specific): {e}"; print(message); return message
    else: return "No new photos were actually processed from the list."

# --- Full Preprocessing Logic (Admin/Initial Scan) ---
def preprocess_event_photos_on_demand():
    print("Admin: Performing full event photo directory scan and processing...")
    temp_encodings_data = []
    processed_this_run_count = 0
    for filename in os.listdir(EVENT_PHOTOS_DIR):
        if not allowed_file(filename): continue
        image_path = os.path.join(EVENT_PHOTOS_DIR, filename)
        print(f"Full scan processing: {image_path}...")
        image_rgb = image_to_rgb(image_path, for_preprocessing=True)
        if image_rgb is None:
            print(f"Full scan: Failed to load {image_path}. Skipping.")
            temp_encodings_data.append({"image_path": image_path, "encodings": [], "error": "load_failed_full_scan"})
            continue
        face_locations = face_recognition.face_locations(image_rgb, model=FACE_DETECTION_MODEL)
        current_image_encodings = face_recognition.face_encodings(image_rgb, face_locations)
        serializable_encodings = [enc.tolist() for enc in current_image_encodings]
        temp_encodings_data.append({"image_path": image_path, "encodings": serializable_encodings})
        if serializable_encodings: print(f"Full scan: Found {len(serializable_encodings)} face(s) in {filename}")
        else: print(f"Full scan: No faces found in {filename}")
        processed_this_run_count += 1
    try:
        with open(ENCODINGS_FILE, 'w') as f: json.dump(temp_encodings_data, f, indent=2)
        message = f"Full scan complete. Processed {processed_this_run_count} photos. Encodings overwritten."
        print(message); return message
    except IOError as e: message = f"Error writing encodings (full scan): {e}"; print(message); return message

# --- Load Encodings ---
def load_known_encodings():
    global KNOWN_ENCODINGS_DATA
    if os.path.exists(ENCODINGS_FILE):
        try:
            with open(ENCODINGS_FILE, 'r') as f: data_from_file = json.load(f)
            temp_known_encodings = []
            for item in data_from_file:
                if "encodings" in item and isinstance(item["encodings"], list) and not item.get("error"):
                    numpy_encodings = [np.array(enc) for enc in item["encodings"] if isinstance(enc, list)]
                    if numpy_encodings: temp_known_encodings.append({"image_path": item["image_path"], "encodings": numpy_encodings})
            KNOWN_ENCODINGS_DATA = temp_known_encodings
            print(f"Encodings loaded: {len(KNOWN_ENCODINGS_DATA)} entries with faces available for matching.")
        except json.JSONDecodeError: print(f"Error: {ENCODINGS_FILE} is corrupted."); KNOWN_ENCODINGS_DATA = []
        except Exception as e: print(f"Unexpected error loading encodings: {e}"); KNOWN_ENCODINGS_DATA = []
    else: print(f"Warning: {ENCODINGS_FILE} not found."); KNOWN_ENCODINGS_DATA = []

# --- Flask Routes ---
@app.route('/')
def index(): return render_template('index.html')

# --- Photographer Routes ---
@app.route('/photographer/upload', methods=['GET'])
def photographer_upload_page(): return render_template('photographer_upload.html')

@app.route('/photographer/upload', methods=['POST'])
def photographer_upload_photos():
    if 'photos' not in request.files: return jsonify({"status": "error", "message": "No photo part"}), 400
    files = request.files.getlist('photos')
    if not files or all(f.filename == '' for f in files): return jsonify({"status": "error", "message": "No selected files"}), 400
    uploaded_count, error_count, errors, newly_saved_paths = 0, 0, [], []
    for file in files:
        if file and allowed_file(file.filename):
            original_filename = secure_filename(file.filename)
            save_path = os.path.join(EVENT_PHOTOS_DIR, original_filename) 
            try:
                file.save(save_path)
                uploaded_count += 1; newly_saved_paths.append(save_path)
            except Exception as e: print(f"Error saving {original_filename}: {e}"); error_count +=1; errors.append(f"Save error for {original_filename}")
        elif file.filename != '': error_count +=1; errors.append(f"File type not allowed: {file.filename}")
    if uploaded_count == 0: return jsonify({"status": "error", "message": f"No valid photos uploaded. Errors: {'; '.join(errors)}"}), 400
    processing_details = "No new photos to process."
    if newly_saved_paths:
        print(f"Photographer upload: {uploaded_count} photos saved. Triggering specific processing...")
        processing_details = process_specific_new_photos(newly_saved_paths)
        load_known_encodings()
    message = f"{uploaded_count} photo(s) uploaded."
    if error_count > 0: message += f" {error_count} photo(s) had errors: {'; '.join(errors)}."
    return jsonify({"status": "success", "message": message, "details": processing_details})

# --- User Search Routes ---
@app.route('/find_my_photos', methods=['POST'])
def find_my_photos():
    print("--- find_my_photos endpoint hit ---")
    if not KNOWN_ENCODINGS_DATA:
        print("find_my_photos: KNOWN_ENCODINGS_DATA is empty, attempting to reload.")
        load_known_encodings()
        if not KNOWN_ENCODINGS_DATA:
            print("find_my_photos: KNOWN_ENCODINGS_DATA still empty after reload.")
            return jsonify({"error": "Encodings not loaded. Try again shortly.", "matches": []}), 503

    data = request.get_json()
    if not data or 'image_data' not in data:
        print("find_my_photos: No image_data in request.")
        return jsonify({"error": "No image data received"}), 400

    image_data_url = data['image_data']
    image_bytes = None
    try:
        header, encoded_data = image_data_url.split(",", 1)
        image_bytes = base64.b64decode(encoded_data)
        print(f"find_my_photos: Received image_bytes length: {len(image_bytes)}, type: {type(image_bytes)}")
        # DEBUG: Save the received image bytes to a file
        debug_filename = "debug_user_selfie.jpg"
        with open(debug_filename, "wb") as f:
            f.write(image_bytes)
        print(f"find_my_photos: Debug selfie saved as {debug_filename}")
    except Exception as e:
        print(f"find_my_photos: Error decoding base64 image: {e}")
        traceback.print_exc()
        return jsonify({"error": "Invalid image data format provided"}), 400
    
    if image_bytes is None: # Should be caught by the try-except above, but as a safeguard
        print("find_my_photos: image_bytes is None after base64 decode attempt.")
        return jsonify({"error": "Failed to get image bytes"}), 400

    # Call image_to_rgb with for_preprocessing=False (default)
    uploaded_image_rgb = image_to_rgb(image_bytes) 

    if uploaded_image_rgb is None: # Check if image_to_rgb failed
        print("find_my_photos: uploaded_image_rgb is None. image_to_rgb failed.")
        return jsonify({"error": "Could not process your image. Please ensure it's a clear photo."}), 400
    
    print("find_my_photos: Successfully converted user image to RGB.")

    user_face_locations = face_recognition.face_locations(uploaded_image_rgb, model=FACE_DETECTION_MODEL)
    print(f"find_my_photos: Found {len(user_face_locations)} face locations in user image.")
    user_face_encodings = face_recognition.face_encodings(uploaded_image_rgb, user_face_locations)

    if not user_face_encodings:
        print("find_my_photos: No face encodings found in user image.")
        return jsonify({"matches": [], "message": "No face detected in your photo. Please try again."})
    
    print(f"find_my_photos: Extracted {len(user_face_encodings)} user face encoding(s).")
    user_encoding = user_face_encodings[0]

    matched_photos_paths = set()
    print(f"find_my_photos: Comparing against {len(KNOWN_ENCODINGS_DATA)} known encoding entries.")
    for item_idx, item in enumerate(KNOWN_ENCODINGS_DATA):
        if not item.get("encodings"): # Ensure "encodings" key exists and is not empty
            # print(f"find_my_photos: Skipping item {item_idx} due to missing or empty encodings.")
            continue
        # print(f"Comparing with known image {item['image_path']} which has {len(item['encodings'])} encodings")
        matches = face_recognition.compare_faces(item["encodings"], user_encoding, tolerance=COMPARISON_TOLERANCE)
        if True in matches:
            print(f"find_my_photos: Match found with {item['image_path']}")
            matched_photos_paths.add(f"/event_photos/{os.path.basename(item['image_path'])}")
    
    if not matched_photos_paths:
        print("find_my_photos: No matches found after comparison.")
        return jsonify({"matches": [], "message": "No photos found matching your face."})

    print(f"find_my_photos: Found {len(matched_photos_paths)} matched photos.")
    return jsonify({"matches": sorted(list(matched_photos_paths))})


@app.route('/event_photos/<path:filename>')
def serve_event_photo(filename):
    return send_from_directory(EVENT_PHOTOS_DIR, os.path.basename(filename))

@app.route('/download/<path:filename>')
def download_file(filename):
    path_to_file = os.path.join(EVENT_PHOTOS_DIR, os.path.basename(filename))
    if os.path.exists(path_to_file) and os.path.isfile(path_to_file):
        try: return send_file(path_to_file, as_attachment=True)
        except Exception as e: print(f"Error sending file {filename}: {e}"); return "Error.", 500
    return "File not found.", 404

# --- Admin Route ---
@app.route('/admin/process_photos', methods=['GET', 'POST']) 
def trigger_preprocessing():
    print("Admin request to process all photos received.")
    try:
        result_message = preprocess_event_photos_on_demand() # The full scan
        load_known_encodings() 
        return jsonify({"status": "success", "message": "Full reprocessing finished.", "details": result_message})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": "Error during full reprocessing.", "details": str(e)}), 500

# --- Main Application Execution ---
if __name__ == '__main__':
    # Initial check and potential preprocessing run at startup
    if not os.path.exists(ENCODINGS_FILE) and os.path.exists(EVENT_PHOTOS_DIR) and len(os.listdir(EVENT_PHOTOS_DIR)) > 0:
        print(f"'{ENCODINGS_FILE}' not found, but event photos exist. Attempting initial full preprocessing...")
        try: preprocess_event_photos_on_demand() # Full scan for initial setup
        except Exception as e: print(f"Error during initial full preprocessing: {e}"); traceback.print_exc()
    
    load_known_encodings() 
    if not KNOWN_ENCODINGS_DATA and os.path.exists(EVENT_PHOTOS_DIR) and len(os.listdir(EVENT_PHOTOS_DIR)) > 0:
        print("WARNING: No face encodings loaded, but event photos exist. Check logs or run admin processing.")

    print("Starting Flask server...")
    # For mobile camera access testing with ngrok, keep host='0.0.0.0' and run ngrok http 5000
    # If using self-signed certs: context = ('cert.pem', 'key.pem'); app.run(..., ssl_context=context)
    app.run(debug=True, host='0.0.0.0', port=5000)