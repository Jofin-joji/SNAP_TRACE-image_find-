# app.py
from flask import Flask, render_template, request, jsonify, send_from_directory, send_file, url_for
import os
import json
import cv2
import numpy as np
import base64
import io
from werkzeug.utils import secure_filename
import time
import traceback

### INSIGHTFACE UPDATE ###
# Import the necessary insightface class. face_recognition is no longer used.
from insightface.app import FaceAnalysis

app = Flask(__name__)

# --- Configuration ---
EVENT_PHOTOS_DIR = "event_photos"
ENCODINGS_FILE = "known_faces_encodings.json"
MAX_PREPROCESSING_SIZE = 1024
### INSIGHTFACE UPDATE ###
# The new threshold for cosine similarity. Higher is a better match.
# A value between 0.5 and 0.6 is a good starting point.
SIMILARITY_THRESHOLD = 0.55
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

# --- Ensure directories exist ---
if not os.path.exists(EVENT_PHOTOS_DIR):
    os.makedirs(EVENT_PHOTOS_DIR)
    print(f"Created directory: {EVENT_PHOTOS_DIR}")

# --- Global variables ---
KNOWN_ENCODINGS_DATA = []
### INSIGHTFACE UPDATE ###
# Initialize a global variable for the FaceAnalysis model.

FACE_APP = None

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
        return cv2.resize(image_cv2, (new_w, new_h), interpolation=cv2.INTER_AREA)
    return image_cv2

def image_to_rgb(image_path_or_bytes, for_preprocessing=False):
    print(f"image_to_rgb: Called. for_preprocessing={for_preprocessing}")
    try:
        img_bgr = None # Initialize
        if isinstance(image_path_or_bytes, str):
            img_bgr = cv2.imread(image_path_or_bytes)
        elif isinstance(image_path_or_bytes, bytes):
            nparr = np.frombuffer(image_path_or_bytes, np.uint8)
            img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        else:
            print(f"image_to_rgb: Received unsupported type: {type(image_path_or_bytes)}")
            return None
        
        if img_bgr is None:
            print(f"image_to_rgb: img_bgr is None after attempting to load/decode.")
            return None

        if for_preprocessing:
            img_bgr = resize_image_if_needed(img_bgr, MAX_PREPROCESSING_SIZE)

        rgb_img = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        return rgb_img
    except Exception as e:
        print(f"CRITICAL ERROR in image_to_rgb: {e}")
        traceback.print_exc()
        return None

### INSIGHTFACE UPDATE ###
# A new helper function to get encodings using the InsightFace model.
# This replaces face_recognition.face_encodings and face_locations.
def get_face_encodings_from_image(image_rgb):
    if FACE_APP is None:
        print("ERROR: InsightFace model (FACE_APP) is not initialized.")
        return []
    try:
        faces = FACE_APP.get(image_rgb)
        # The 'embedding' is the face encoding vector
        return [face['embedding'] for face in faces]
    except Exception as e:
        print(f"Error during InsightFace processing: {e}")
        traceback.print_exc()
        return []

# --- Optimized Preprocessing for Specific Files ---
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
        
        ### INSIGHTFACE UPDATE ###
        # Use the new helper function for getting encodings.
        current_image_encodings = get_face_encodings_from_image(image_rgb)
        
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

        ### INSIGHTFACE UPDATE ###
        # Use the new helper function for getting encodings.
        current_image_encodings = get_face_encodings_from_image(image_rgb)

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
    
    ### FIX ###: Added a master try...except block to catch all errors.
    try:
        if not KNOWN_ENCODINGS_DATA:
            load_known_encodings()
            if not KNOWN_ENCODINGS_DATA:
                print("find_my_photos: KNOWN_ENCODINGS_DATA is empty even after reload.")
                return jsonify({"error": "Server is processing photos. Please try again in a moment.", "matches": []}), 503

        data = request.get_json()
        if not data or 'image_data' not in data:
            return jsonify({"error": "No image data received"}), 400

        try:
            _, encoded_data = data['image_data'].split(",", 1)
            image_bytes = base64.b64decode(encoded_data)
        except Exception as e:
            print(f"Error decoding base64 string: {e}")
            return jsonify({"error": "Invalid image data format provided"}), 400
        
        uploaded_image_rgb = image_to_rgb(image_bytes)
        if uploaded_image_rgb is None:
            return jsonify({"error": "Could not process your image. Please ensure it's a clear photo."}), 400
        
        user_face_encodings = get_face_encodings_from_image(uploaded_image_rgb)
        
        if not user_face_encodings:
            return jsonify({"matches": [], "message": "No face detected in your photo. Please try again."})
        
        user_encoding = user_face_encodings[0]
        
        ### FIX ###: Check for zero-norm before dividing.
        user_norm = np.linalg.norm(user_encoding)
        if user_norm == 0:
            print("Error: User face encoding resulted in a zero-vector.")
            return jsonify({"error": "Could not generate a valid face profile from your photo.", "matches": []}), 400
        user_encoding_norm = user_encoding / user_norm

        matched_photos_paths = set()
        print(f"Comparing user face against {len(KNOWN_ENCODINGS_DATA)} known photos.")
        for item in KNOWN_ENCODINGS_DATA:
            if not item.get("encodings"):
                continue
            
            for known_encoding in item["encodings"]:
                ### FIX ###: Add the same defensive check for the known encodings.
                known_norm = np.linalg.norm(known_encoding)
                if known_norm == 0:
                    continue # Skip this invalid encoding
                    
                known_encoding_norm = known_encoding / known_norm
                
                similarity = np.dot(user_encoding_norm, known_encoding_norm)
                
                if similarity > SIMILARITY_THRESHOLD:
                    print(f"Match found! Photo: {item['image_path']}, Similarity: {similarity:.4f}")
                    matched_photos_paths.add(f"/event_photos/{os.path.basename(item['image_path'])}")
                    break
        
        if not matched_photos_paths:
            return jsonify({"matches": [], "message": "No photos found matching your face."})

        return jsonify({"matches": sorted(list(matched_photos_paths))})

    except Exception as e:
        # This block will catch any unexpected error, log it, and send a clean JSON response.
        print(f"FATAL ERROR in /find_my_photos: {e}")
        traceback.print_exc() # This will print the detailed error to your server console
        return jsonify({"error": "An unexpected server error occurred. Please contact support.", "matches": []}), 500
    ### INSIGHTFACE UPDATE ###
    # Get user's face encoding using the new model.
    user_face_encodings = get_face_encodings_from_image(uploaded_image_rgb)
    
    if not user_face_encodings:
        return jsonify({"matches": [], "message": "No face detected in your photo. Please try again."})
    
    # We only use the first detected face from the user's selfie.
    user_encoding = user_face_encodings[0]
    # Normalize the user's encoding for cosine similarity calculation.
    user_encoding_norm = user_encoding / np.linalg.norm(user_encoding)

    matched_photos_paths = set()
    print(f"Comparing user face against {len(KNOWN_ENCODINGS_DATA)} known photos.")
    for item in KNOWN_ENCODINGS_DATA:
        if not item.get("encodings"): continue
        
        # ### INSIGHTFACE UPDATE ###
        # # The core comparison logic is now based on cosine similarity.
        for known_encoding in item["encodings"]:
            # Normalize each known encoding
            known_encoding_norm = known_encoding / np.linalg.norm(known_encoding)
            
            # Calculate cosine similarity
            similarity = np.dot(user_encoding_norm, known_encoding_norm)
            
            if similarity > SIMILARITY_THRESHOLD:
                print(f"Match found! Photo: {item['image_path']}, Similarity: {similarity:.4f}")
                matched_photos_paths.add(f"/event_photos/{os.path.basename(item['image_path'])}")
                # Once a match is found in a photo, we don't need to check other faces in it
                break 
    
    if not matched_photos_paths:
        return jsonify({"matches": [], "message": "No photos found matching your face."})

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
        # NOTE: If you run this, all old encodings will be replaced with new,
        # higher quality InsightFace encodings. This is required.
        result_message = preprocess_event_photos_on_demand()
        load_known_encodings() 
        return jsonify({"status": "success", "message": "Full reprocessing finished.", "details": result_message})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": "Error during full reprocessing.", "details": str(e)}), 500

# --- Main Application Execution ---
# --- Main Application Execution ---
if __name__ == '__main__':
    # Initialize the FaceAnalysis model when the app starts.
    # This is crucial for performance as the model is loaded into memory only once.
    print("Initializing InsightFace model (buffalo_l)... This may take a moment.")
    try:
        # For CPU usage
        FACE_APP = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
        
        # --- UNCOMMENT FOR GPU USAGE ---
        # If you have a compatible NVIDIA GPU and have installed 'onnxruntime-gpu', use this instead:
        # print("Attempting to use CUDA (GPU) for InsightFace.")
        # FACE_APP = FaceAnalysis(name='buffalo_l', providers=['CUDAExecutionProvider', 'CPUExecutionProvider'])
        
        FACE_APP.prepare(ctx_id=0, det_size=(640, 640))
        print("InsightFace model initialized successfully.")
    except Exception as e:
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print(f"FATAL ERROR: Could not initialize InsightFace model: {e}")
        print("Please ensure 'insightface' and 'onnxruntime' (or 'onnxruntime-gpu') are installed correctly.")
        print("pip install insightface==0.7.3 onnxruntime")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        # Exit the application if the core component fails to load.
        exit()


    # IMPORTANT: This block handles the critical step of ensuring your encodings
    # match the model you are using (InsightFace).
    if not os.path.exists(ENCODINGS_FILE) and os.path.exists(EVENT_PHOTOS_DIR) and len(os.listdir(EVENT_PHOTOS_DIR)) > 0:
        print(f"'{ENCODINGS_FILE}' not found. Starting initial full preprocessing with InsightFace...")
        print("This will generate new 512-dimension encodings for all photos.")
        try:
            preprocess_event_photos_on_demand()
        except Exception as e:
            print(f"Error during initial full preprocessing: {e}")
            traceback.print_exc()

    # Always load whatever encodings are available after the potential preprocessing step.
    load_known_encodings()

    if not KNOWN_ENCODINGS_DATA and os.path.exists(EVENT_PHOTOS_DIR) and len(os.listdir(EVENT_PHOTOS_DIR)) > 0:
        print("-----------------------------------------------------------------------------------")
        print("WARNING: No face encodings were loaded, but photos exist in the event directory.")
        print(f"This could mean the '{ENCODINGS_FILE}' is empty or corrupted.")
        print("You may need to manually delete the file and restart, or hit the /admin/process_photos endpoint.")
        print("-----------------------------------------------------------------------------------")

    print("Starting Flask server...")
    # The 'debug=True' setting is great for development, as it provides detailed error pages
    # and automatically reloads the server when you save changes.
    app.run(debug=True, host='0.0.0.0', port=5000)