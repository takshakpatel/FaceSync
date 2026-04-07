# FaceSync: Real-Time Biometric Recognition System

![FaceSync Dashboard](https://img.shields.io/badge/Status-Active-success) ![Python](https://img.shields.io/badge/Python-3.8+-blue.svg) ![OpenCV](https://img.shields.io/badge/OpenCV-4.x-green.svg) ![DeepFace](https://img.shields.io/badge/DeepFace-ArcFace-orange.svg)

FaceSync is a high-performance, real-time facial recognition web application. It combines the blazing-fast detection speeds of OpenCV Haar Cascades with the state-of-the-art accuracy of the ArcFace neural network, all wrapped in a sleek, glassmorphism web dashboard.

## Features

* **Low Latency Streaming:** Custom multi-threaded background buffer flushing guarantees zero-lag live capture from local webcams and network IP cameras.
* **Hybrid Recognition Engine:** Uses lightweight OpenCV cascades for 30fps tracking and periodically extracts heavy Deep Learning embeddings to maintain maximum performance.
* **Mobile IP Camera Support:** Readily accepts URL streams from smartphone IP Camera apps out-of-the-box using FFmpeg backend optimization.
* **Instant Auto-Enrollment:** Instantly detects, crops, and enrolls faces via an intuitive web dashboard without server restarts.
* **Dynamic Event Log:** Real-time push updates of who is currently on screen alongside confidence percentages.

##  Installation

**1. Clone the repository and install requirements**
```bash
git clone https://github.com/takshakpatel/FaceSync.git
cd FaceSync
pip install -r backend/requirements.txt
```

**2. Start the Server**
```bash
python backend/app.py
```
*(Note: On your very first run, DeepFace will automatically download the 137MB ArcFace model weights).*

**3. Open the Dashboard**
Navigate to `http://localhost:5000` in your web browser.

##  Using a Mobile Phone as a Camera
1. Install a free IP Camera app on your smartphone (e.g., "IP Webcam" on Android).
2. Connect your phone and PC to the same Wi-Fi network and start the server on your phone.
3. In the FaceSync dashboard, select "Mobile IP Camera" from the dropdown.
4. Enter your stream URL (e.g., `http://192.168.1.10:8080/video`). Ensure you include the `/video` endpoint!

##  Tech Stack
* **Backend Framework:** Flask + SQLite
* **Computer Vision:** OpenCV + DeepFace (ArcFace model)
* **Frontend:** Vanilla JS + CSS (Glassmorphism UI)
