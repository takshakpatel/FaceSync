import os
import cv2
import json
import time
from flask import Flask, Response, request, jsonify, render_template
from flask_cors import CORS

from database import init_db, get_events, get_enrolled_faces, delete_enrolled_face
from camera import Camera
from face_engine import FaceEngine

app = Flask(__name__, 
            static_folder='../frontend', 
            static_url_path='/',
            template_folder='../frontend')
CORS(app)

# Initialize DB
init_db()

# Globals for engine and camera
engine = None
video_camera = None

def get_engine():
    global engine
    if engine is None:
        engine = FaceEngine()
    return engine

def get_camera():
    global video_camera
    if video_camera is None:
        video_camera = Camera(index=0)
    return video_camera

def generate_frames():
    cam = get_camera()
    eng = get_engine()
    
    while True:
        frame, success = cam.get_frame()
        if not success:
            time.sleep(0.1)
            continue
            
        # Process frame
        processed_frame, recognized = eng.process_frame(frame)
        
        # Encode
        ret, buffer = cv2.imencode('.jpg', processed_frame)
        if not ret:
            continue
            
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/camera', methods=['POST'])
def update_camera():
    data = request.json
    index = data.get('index', 0)
    cam = get_camera()
    success = cam.change_source(index)
    if success:
        return jsonify({"status": "success"})
    else:
        return jsonify({"status": "error", "message": "Failed to open camera index"}), 400

@app.route('/api/enroll', methods=['POST'])
def enroll():
    if 'image' not in request.files or 'name' not in request.form:
        return jsonify({"status": "error", "message": "Missing image or name"}), 400
    
    name = request.form['name']
    image_file = request.files['image']
    
    eng = get_engine()
    success, message = eng.enroll(name, image_file)
    
    if success:
        return jsonify({"status": "success", "message": message})
    else:
        return jsonify({"status": "error", "message": message}), 400

@app.route('/api/faces', methods=['GET'])
def list_faces():
    faces = get_enrolled_faces()
    return jsonify(faces)

@app.route('/api/faces/<name>', methods=['DELETE'])
def delete_face(name):
    delete_enrolled_face(name)
    eng = get_engine()
    if name in eng.known_embeddings:
        del eng.known_embeddings[name]
    return jsonify({"status": "success"})

@app.route('/api/events', methods=['GET'])
def list_events():
    limit = int(request.args.get('limit', 50))
    events = get_events(limit)
    return jsonify(events)

@app.route('/api/status', methods=['GET'])
def get_status():
    eng = get_engine()
    cam = get_camera()
    return jsonify({
        "status": "online",
        "enrolled_count": len(eng.known_embeddings),
        "camera_index": cam.index,
        "camera_active": cam.video.isOpened()
    })

if __name__ == '__main__':
    # Initialize engine early to pre-load deepface model
    get_engine()
    app.run(host='0.0.0.0', port=5000, threaded=True)
