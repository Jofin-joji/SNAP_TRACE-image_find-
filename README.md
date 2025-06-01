# SnapTrace - AI-Powered Event Photo Finder

SnapTrace is a web application designed to help users quickly find their photos from large event galleries using facial recognition. Photographers can upload event photos, and users can then use their device's camera to find images containing their face.

## Features

- **User Photo Search:** Users can capture their face via webcam/device camera to search for their photos.
- **Photographer Upload Portal:** A dedicated interface for photographers to upload event photos.
- **Face Recognition:** Utilizes the `face_recognition` library (based on dlib) to detect faces and extract encodings.
- **Efficient Search:**
  - Pre-processes uploaded event photos to extract and store face encodings.
  - Optimized comparison of user's face encoding against stored encodings.
- **Thumbnail Display:** Shows fast-loading thumbnails of matched photos, with an option to download the full-resolution original.
- **Web Interface:** Built with Flask (Python backend) and HTML/CSS/JavaScript (frontend).
- **Responsive Design:** Basic responsiveness for desktop and mobile viewing.

## Project Structure

snaptrace/
├── app.py # Main Flask application logic
├── templates/
│ ├── \_base.html # Base template for navbar and footer
│ ├── index.html # User photo search page
│ └── photographer_upload.html # Photographer photo upload page
├── static/
│ ├── css/
│ │ └── style.css # Main stylesheet
│ └── js/
│ └── script.js # Client-side JavaScript for user search page
├── event_photos/ # Directory to store original uploaded event photos
├── event_photos_thumbnails/ # Directory to store generated thumbnails
├── known_faces_encodings.json # Stores pre-processed face encodings and image info
├── cert.pem # (Optional) SSL certificate for self-signed HTTPS
├── key.pem # (Optional) SSL private key for self-signed HTTPS
└── README.md # This file

## Prerequisites

- **Python 3.8+**
- **pip** (Python package installer)
- **CMake:** Required by `dlib` (a dependency of `face_recognition`).
  - Windows: Install from [cmake.org](https://cmake.org/download/) and ensure it's added to your PATH.
  - Linux: `sudo apt-get install build-essential cmake` or `sudo yum install cmake gcc-c++`
  - macOS: `brew install cmake`
- **C++ Compiler:** `dlib` also needs a C++ compiler.
  - Windows: Visual Studio with C++ development tools (Community edition is free).
  - Linux: `build-essential` or `gcc-c++` (usually installed with CMake command above).
  - macOS: Xcode Command Line Tools (`xcode-select --install`).
- **(Optional for HTTPS) OpenSSL:** For generating self-signed certificates if not using ngrok.
  - Often included with Git for Windows or can be installed separately.
- **(Optional for Mobile Testing) ngrok:** For exposing your local server via a public HTTPS URL.
  - Download from [ngrok.com](https://ngrok.com).
  - Sign up for a free account and [get your authtoken](https://dashboard.ngrok.com/get-started/your-authtoken).

## Setup Instructions

1.  **Clone the Repository:**

    ```bash
    git clone https://github.com/YOUR_USERNAME/snaptrace.git
    cd snaptrace
    ```

2.  **Create a Python Virtual Environment:**
    It's highly recommended to use a virtual environment to manage project dependencies.

    ```bash
    python -m venv venv
    ```

    Activate the virtual environment:

    - Windows: `venv\Scripts\activate`
    - macOS/Linux: `source venv/bin/activate`

3.  **Install Dependencies:**
    Make sure you have CMake and a C++ compiler installed _before_ running this step, as `dlib` (a dependency of `face_recognition`) needs them.

    ```bash
    pip install Flask face_recognition opencv-python numpy Werkzeug
    ```

    - If you encounter issues installing `dlib` or `face_recognition`, refer to their respective documentation for platform-specific troubleshooting. This is often the trickiest part of the setup.

4.  **Create Necessary Directories (if not already present):**
    The application will create these on first run if they don't exist, but you can create them manually:

    ```bash
    mkdir event_photos
    mkdir event_photos_thumbnails
    ```

5.  **(Optional - For `ngrok` Usage) Configure ngrok Authtoken:**
    If you plan to use `ngrok` for mobile testing, configure your authtoken (you only need to do this once per machine):
    - Navigate to where you downloaded `ngrok.exe` (or the `ngrok` binary).
    - Run:
      ```bash
      # For PowerShell if ngrok is in the current directory:
      .\ngrok config add-authtoken YOUR_NGROK_AUTHTOKEN
      # For CMD or if ngrok is in PATH:
      ngrok config add-authtoken YOUR_NGROK_AUTHTOKEN
      ```
      Replace `YOUR_NGROK_AUTHTOKEN` with the token from your ngrok dashboard.

## Running the Application

There are two main ways to run the application, primarily differing in how you handle HTTPS for camera access on devices other than `localhost`.

**Method 1: Running on HTTP (Recommended for local development & `ngrok` usage)**

This is the simplest way to get the server running. You'll use `ngrok` to access it from mobile devices.

1.  **Ensure `app.py` is configured for HTTP:**
    At the end of `app.py`, the `app.run()` line should look like this:

    ```python
    if __name__ == '__main__':
        # ... (startup logic) ...
        print("Starting Flask server on HTTP (for ngrok/localhost)...")
        app.run(debug=True, host='0.0.0.0', port=5000)
    ```

2.  **Start the Flask Application:**
    In your project directory (`snaptrace/`), with the virtual environment activated, run:

    ```bash
    python app.py
    ```

    The server will start, typically on `http://0.0.0.0:5000`. You'll see console output indicating it's running and if initial preprocessing occurs.

3.  **Initial Preprocessing:**

    - If this is the first run and you have images in the `event_photos/` directory, the application will attempt to preprocess them (generate encodings and thumbnails). This might take some time. Monitor the console.
    - If `event_photos/` is empty, no preprocessing will occur initially.

4.  **Accessing the Application:**
    - **On your computer (localhost):** Open a web browser and go to `http://localhost:5000` or `http://127.0.0.1:5000`. Camera access should work directly.
    - **For Mobile Devices or Other Computers on the Same Network (Requires `ngrok` for camera):**
      a. Open a **NEW, SEPARATE terminal window/tab**.
      b. Navigate to where your `ngrok` executable is located.
      c. Run `ngrok` to create a tunnel to your local Flask server:
      `bash
    # For PowerShell if ngrok is in the current directory:
    .\ngrok http 5000
    # For CMD or if ngrok is in PATH:
    ngrok http 5000
    `
      d. `ngrok` will display a "Forwarding" URL that starts with `https://` (e.g., `https://<random-string>.ngrok-free.app`).
      e. Open **this `https://...` URL** in the browser on your mobile device or other computer. Camera access will now work because the connection is over HTTPS via ngrok.

**Method 2: Running with Self-Signed HTTPS (Alternative, involves browser warnings)**

This method makes Flask serve HTTPS directly. It's useful if you don't want to use `ngrok` but requires generating SSL certificates and dealing with browser security warnings.

1.  **Generate Self-Signed SSL Certificates:**

    - Open a terminal/command prompt in your project directory (`snaptrace/`).
    - Run the OpenSSL command (ensure OpenSSL is installed and in your PATH):
      ```bash
      openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365
      ```
    - Answer the prompts (dummy information is fine for local development). This will create `cert.pem` and `key.pem` in your project directory.

2.  **Modify `app.py` to use `ssl_context`:**
    At the end of `app.py`, change the `app.run()` section to:

    ```python
    if __name__ == '__main__':
        # ... (startup logic) ...
        context = ('cert.pem', 'key.pem') # Ensure these files exist
        print("Starting Flask server with self-signed HTTPS...")
        app.run(debug=True, host='0.0.0.0', port=5000, ssl_context=context)
    ```

3.  **Start the Flask Application:**

    ```bash
    python app.py
    ```

    The server will start on `https://0.0.0.0:5000`.

4.  **Accessing the Application:**
    - Open a web browser and go to `https://localhost:5000` or `https://YOUR_COMPUTER_IP:5000` (e.g., `https://192.168.1.10:5000`).
    - **Your browser will display a security warning** (e.g., "Your connection is not private"). This is expected because the certificate is self-signed.
    - You'll need to find an option like "Advanced" and "Proceed to ... (unsafe)" to continue to the site.
    - Once you bypass the warning, camera access should work.

## Using the Application

1.  **Photographer Portal:**

    - Navigate to `/photographer/upload` (e.g., `http://localhost:5000/photographer/upload` or the ngrok equivalent).
    - Select image files (JPG, JPEG, PNG) and click "Upload & Process Photos."
    - Uploaded photos will be saved to `event_photos/`, thumbnails to `event_photos_thumbnails/`, and their face encodings will be processed and added to `known_faces_encodings.json`.

2.  **User Photo Search (Find My Photos):**

    - Navigate to the main page (`/`, e.g., `http://localhost:5000` or the ngrok equivalent).
    - Allow camera access when prompted by the browser.
    - Position your face clearly in the video feed.
    - Click "Find My Photos."
    - The application will capture your face, extract its encoding, and compare it against all processed event photos.
    - Matched photos (as thumbnails) will be displayed.
    - Click "Download" on any matched photo to get the full-resolution original.

3.  **Admin - Full Reprocessing (Optional):**
    - Navigate to `/admin/process_photos`.
    - This endpoint will re-scan the entire `event_photos/` directory, re-generate all encodings and thumbnails, and overwrite `known_faces_encodings.json`. Useful if you manually added/removed photos or want a fresh processing run.
    - **Security Note:** In a production environment, this admin endpoint should be protected by authentication.

## Troubleshooting

- **`dlib` or `face_recognition` installation issues:** This is common. Ensure CMake and a C++ compiler are correctly installed and accessible. Consult `dlib` and `face_recognition` installation guides for your specific OS.
- **Camera Not Working on Mobile/Other Devices:** This is almost always due to not using HTTPS. Use `ngrok` (Method 1) or set up self-signed SSL (Method 2) and ensure you are accessing the `https://` URL. Also, check browser permissions for camera access for the site.
- **`FileNotFoundError` for `cert.pem`/`key.pem`:** If using self-signed SSL (Method 2), ensure these files have been generated and are in the same directory as `app.py`, and that their names match what's in the `ssl_context` tuple.
- **`ngrok` `ERR_NGROK_4018` (Authentication Failed):** You need to sign up for a free ngrok account and configure your authtoken using `ngrok config add-authtoken YOUR_TOKEN`.
- **Slow Loading of Matched Photos:** This README assumes the thumbnail implementation is in place. If images still load slowly, ensure thumbnails are being generated and used for display.
- **No Encodings Loaded:** If the console shows "0 total face encodings loaded," check the `known_faces_encodings.json` file structure and the console output during preprocessing to see if faces were detected or if errors occurred.

## Future Enhancements

- User accounts and authentication (especially for photographer and admin).
- More robust error handling and user feedback.
- Database for storing encodings and image metadata for better scalability.
- Background task queue (e.g., Celery) for preprocessing large batches of photos without blocking upload requests.
- Advanced UI/UX features (e.g., photo tagging, albums).
- Deployment to a cloud platform.

---

This README provides a good starting point. You can add more specific details about your project's unique aspects or further development plans.
