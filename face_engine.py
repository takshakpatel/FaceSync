import os
import cv2
import time
import threading
import numpy as np
from deepface import DeepFace
from datetime import datetime
from PIL import Image

import database

class FaceEngine:
    def __init__(self):
        # Pre-build model so it downloads synchronously on startup
        DeepFace.build_model('ArcFace')
        
        # OpenCV Haar Cascade for fast face detection
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        self.face_cascade = cv2.CascadeClassifier(cascade_path)
        
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'faces')
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Load known faces from DB to memory
        self.known_embeddings = {} # name -> embedding
        self.lock = threading.Lock()
        
        # Pre-load embeddings
        self._load_embeddings()
        
        # Throttling logging and recognition
        self.last_logged = {}
        self.frame_count = 0
        self.last_recognitions = []

    def _load_embeddings(self):
        faces = database.get_enrolled_faces()
        for face in faces:
            name = face['name']
            path = face['image_path']
            if os.path.exists(path):
                try:
                    # 'ArcFace' is fast and accurate
                    embedding_objs = DeepFace.represent(img_path=path, model_name='ArcFace', enforce_detection=False)
                    if embedding_objs:
                        self.known_embeddings[name] = embedding_objs[0]['embedding']
                except Exception as e:
                    print(f"Error loading embedding for {name}: {e}")

    def enroll(self, name, image_file):
        with self.lock:
            # Save original image
            os.makedirs(self.data_dir, exist_ok=True)
            filename = f"{name.replace(' ', '_')}_{int(time.time())}.jpg"
            filepath = os.path.join(self.data_dir, filename)
            
            # Save original image resized to prevent DeepFace from hanging on huge files
            img = Image.open(image_file.stream if hasattr(image_file, 'stream') else image_file)
            img = img.convert('RGB')
            img.thumbnail((800, 800))
            img.save(filepath)
            
            # Extract embedding using ArcFace
            try:
                embedding_objs = DeepFace.represent(img_path=filepath, model_name='ArcFace', enforce_detection=True)
                if embedding_objs:
                    self.known_embeddings[name] = embedding_objs[0]['embedding']
                    success = database.enroll_face(name, filepath)
                    if not success:
                        return False, "User with this name already exists"
                    return True, "Enrolled successfully"
                else:
                    os.remove(filepath)
                    return False, "No face found in image"
            except Exception as e:
                if os.path.exists(filepath):
                    os.remove(filepath)
                return False, f"Error processing face: {str(e)}"

    def _cosine_similarity(self, a, b):
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

    def process_frame(self, frame):
        self.frame_count += 1
        
        # Downscale for much faster Haar detection
        oh, ow = frame.shape[:2]
        small_frame = cv2.resize(frame, (640, int(640 * oh / ow)))
        
        gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) # Still use full res RGB for embedding extraction
        
        # Detect faces using Haar Cascade (fast, no external dependencies)
        faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
        
        scale_x = ow / 640.0
        scale_y = oh / int(640 * oh / ow)
        
        current_recognitions = []
        run_heavy = (self.frame_count % 10 == 0) # Only run Neural Net every 10 frames
        
        if len(faces) > 0:
            for (sx, sy, sw, sh) in faces:
                x = int(sx * scale_x)
                y = int(sy * scale_y)
                w = int(sw * scale_x)
                h = int(sh * scale_y)
                
                match_name = "Unknown"
                confidence = 0.0
                
                # Check cache for recent recognitions nearby (IoU approximation)
                center_x, center_y = x + w/2, y + h/2
                matched_cache = None
                for last in self.last_recognitions:
                    lx, ly, lw, lh = last['box']
                    lc_x, lc_y = lx + lw/2, ly + lh/2
                    if abs(center_x - lc_x) < w and abs(center_y - lc_y) < h:
                        match_name = last['name']
                        confidence = last['confidence']
                        matched_cache = last
                        break
                
                # Recognition logic if known faces exist AND (we need to update OR no cache found)
                if self.known_embeddings and (run_heavy or matched_cache is None):
                    # Expand box slightly for better extraction
                    pad_w = int(w * 0.1)
                    pad_h = int(h * 0.1)
                    x1 = max(0, x - pad_w)
                    y1 = max(0, y - pad_h)
                    x2 = min(ow, x + w + pad_w)
                    y2 = min(oh, y + h + pad_h)
                    
                    face_img = rgb_frame[y1:y2, x1:x2]
                    if face_img.size > 0:
                        try:
                            # Extract embedding without enforcing detection again
                            curr_embedding_objs = DeepFace.represent(img_path=face_img, model_name='ArcFace', enforce_detection=False)
                            if curr_embedding_objs:
                                curr_emb = curr_embedding_objs[0]['embedding']
                                
                                best_match_score = -1
                                best_match_name = None
                                
                                for name, ext_emb in self.known_embeddings.items():
                                    score = self._cosine_similarity(curr_emb, ext_emb)
                                    if score > best_match_score:
                                        best_match_score = score
                                        best_match_name = name
                                
                                # ArcFace threshold
                                if best_match_score > 0.68:
                                    match_name = best_match_name
                                    confidence = best_match_score
                        except Exception as e:
                            pass
                
                current_recognitions.append({
                    "name": match_name,
                    "confidence": float(confidence),
                    "box": (x, y, w, h)
                })
                
                # Logging throttling (once every 5 seconds per recognized person)
                current_time = time.time()
                if match_name != "Unknown":
                    if match_name not in self.last_logged or (current_time - self.last_logged[match_name]) > 5:
                        database.log_event(match_name, float(confidence), None)
                        self.last_logged[match_name] = current_time
                
                # Draw box
                color = (0, 255, 0) if match_name != "Unknown" else (0, 0, 255)
                cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
                # Draw label
                label = f"{match_name} ({confidence*100:.1f}%)" if match_name != "Unknown" else "Unknown"
                cv2.putText(frame, label, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                
        self.last_recognitions = current_recognitions
        return frame, current_recognitions
