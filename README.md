# 📸 SnapTrace – AI-Powered Event Photo Finder

**SnapTrace** is a smart, AI-driven web application that allows event attendees to easily find their personal photos in large photo galleries using **facial recognition**. Just upload a selfie, and SnapTrace will locate every image containing your face – all with incredible accuracy and speed.

---

## 🚀 Features

- 🔍 **User-Friendly Photo Search**  
  Upload a selfie or use your webcam to search through thousands of event photos.

- 📤 **Photographer Upload Portal**  
  A dedicated interface for photographers to bulk upload photos from events.

- 🤖 **State-of-the-Art Face Recognition**

  - Powered by **[InsightFace](https://github.com/deepinsight/insightface)** (`buffalo_l` model).
  - Generates **512-dimensional facial embeddings** for precise identity matching.

- ⚡ **Efficient & Accurate Matching**

  - Photos are preprocessed with face detection and embedding generation.
  - Uses **Cosine Similarity** to match user selfies against the gallery.

- ⚙️ **Robust Backend & Responsive Frontend**

  - Built with **Flask (Python)** backend.
  - Clean and responsive **HTML/CSS/JavaScript** frontend.

- 🖼️ **Instant Results**
  - Matched photos are displayed immediately.
  - Full-resolution originals are available for download.

---

## 📁 Project Structure

<pre lang="text"><code>snaptrace/ ├── app.py # Main Flask application logic ├── templates/ # HTML templates │ ├── _base.html # Base layout (optional) │ ├── index.html # User selfie search page │ └── photographer_upload.html # Photographer upload page ├── static/ # Static assets │ ├── css/ │ │ └── style.css # Main stylesheet │ └── js/ │ └── script.js # Camera & search logic ├── event_photos/ # Uploaded event photos ├── known_faces_encodings.json # Stores face embeddings + image paths ├── README.md # Project documentation ├── requirements.txt # Project dependencies ├── cert.pem # (Optional) SSL certificate └── key.pem # (Optional) SSL private key </code></pre>

---

## 🛠️ Prerequisites

- **Python 3.8+**
- **pip** (Python package installer)
- **ngrok** (Optional, for mobile browser camera access via HTTPS)  
  Get it from: https://ngrok.com  
  Run: `ngrok config add-authtoken YOUR_TOKEN`

> ✅ No need for `dlib`, `CMake`, or a C++ compiler – setup is simple!

---

## ⚙️ Setup Instructions

📦 Clone the Repository

```bash
git clone https://github.com/Jofin-joji/snaptrace.git
cd snaptrace


📚 Install Dependencies
bash
Copy
Edit
pip install Flask insightface==0.7.3 onnxruntime opencv-python numpy Werkzeug
💡 For NVIDIA GPU users:
Enable GPU acceleration:

bash
Copy
Edit
pip uninstall onnxruntime
pip install onnxruntime-gpu
Uncomment the CUDAExecutionProvider line in app.py.


▶️ Running the Application
bash
Copy
Edit
python app.py
On first run, InsightFace will download the required buffalo_l model.

If known_faces_encodings.json does not exist, the app will automatically preprocess all faces in event_photos/.

🌐 Accessing the Application
💻 Desktop
Open your browser and go to:
http://localhost:5000

📱 Mobile (Requires HTTPS for camera access)
Open a terminal window and run:

bash
Copy
Edit
ngrok http 5000
Copy the generated https://<random>.ngrok-free.app URL.

Open this URL on your mobile browser – the camera should now work.

🧑‍💻 Using the Application
📤 Photographer Upload Portal
Visit: http://localhost:5000/photographer/upload

Upload images (JPG, JPEG, PNG).

All faces are detected, and embeddings are saved to known_faces_encodings.json.

🔍 User Photo Search
Visit the homepage: http://localhost:5000/

Grant camera access.

Click Find My Photos – matched images will be displayed instantly.

🔄 Admin: Reprocess All Photos
Visit: http://localhost:5000/admin/process_photos

This forces reprocessing of all images in event_photos/.
```
