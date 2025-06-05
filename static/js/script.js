document.addEventListener('DOMContentLoaded', () => {
    const videoElement = document.getElementById('videoElement');
    const canvasElement = document.getElementById('canvasElement');
    const captureButton = document.getElementById('captureButton');
    const resultsGrid = document.getElementById('resultsGrid'); // Updated ID
    const statusMessageDiv = document.getElementById('statusMessage'); // Updated ID
    const resultsContainer = document.getElementById('results-container');

    let stream;

    async function setStatus(message, type = 'info') {
        statusMessageDiv.textContent = message;
        statusMessageDiv.className = `status-message ${type}`; // e.g. status-message info, status-message error
    }

    async function startCamera() {
        try {
            stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' } });
            videoElement.srcObject = stream;
            setStatus("Camera ready. Position your face and click 'Scan My Face'.", 'info');
        } catch (err) {
            console.error("Error accessing camera: ", err);
            setStatus(`Could not access camera: ${err.name}. Check permissions.`, 'error');
        }
    }

    captureButton.addEventListener('click', async () => {
        if (!stream || !videoElement.srcObject) {
            setStatus("Camera not active. Please allow access.", 'error');
            startCamera(); 
            return;
        }

        setStatus("Scanning your face... please wait.", 'processing');
        resultsGrid.innerHTML = ''; 
        resultsContainer.style.display = 'none';
        captureButton.disabled = true;
        captureButton.textContent = 'Scanning...';


        canvasElement.width = videoElement.videoWidth;
        canvasElement.height = videoElement.videoHeight;

        const context = canvasElement.getContext('2d');
        context.drawImage(videoElement, 0, 0, canvasElement.width, canvasElement.height);
        const imageDataURL = canvasElement.toDataURL('image/jpeg', 0.9);

        try {
            const response = await fetch('/find_my_photos', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', },
                body: JSON.stringify({ image_data: imageDataURL }),
            });

            const data = await response.json(); 

            if (!response.ok) {
                const errorMsg = data.error || `Server error (${response.status}). Try again.`;
                setStatus(errorMsg, 'error');
                console.error("Server error data:", data);
                return;
            }

            if (data.error) {
                 setStatus(`Error: ${data.error}`, 'error');
            } else if (data.matches && data.matches.length > 0) {
                setStatus(`Found ${data.matches.length} photo(s) of you!`, 'success');
                resultsContainer.style.display = 'block'; 
                data.matches.forEach(imagePath => {
                    const photoCardDiv = document.createElement('div'); // Changed class name
                    photoCardDiv.classList.add('photo-card'); // Changed class name

                    const img = document.createElement('img');
                    img.src = imagePath; 
                    img.alt = "Matched photo";
                    img.loading = "lazy"; // Lazy load images
                    
                    const downloadLink = document.createElement('a');
                    const filename = imagePath.split('/').pop();
                    downloadLink.href = `/download/${filename}`;
                    downloadLink.textContent = `Download`;
                    downloadLink.classList.add('download-link');
                    downloadLink.setAttribute('download', filename); 
                    photoCardDiv.appendChild(img);
                    photoCardDiv.appendChild(downloadLink);
                    resultsGrid.appendChild(photoCardDiv);
                });
            } else {
                setStatus(data.message || "No matches found for your face.", 'info');
            }
        } catch (error) {
            console.error('Error finding photos:', error);
            setStatus(`Client-side error: ${error.message}.`, 'error');
        } finally {
            captureButton.disabled = false;
            captureButton.textContent = 'Scan My Face';
        }
    });

    startCamera();
});