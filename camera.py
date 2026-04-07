import cv2
import threading
import time

class Camera:
    def __init__(self, index=0):
        self.lock = threading.Lock()
        self.frame = None
        self.success = False
        self.running = True
        self.open_source(index)
        
        # Start background thread to clear buffers and get newest frame instantly
        self.thread = threading.Thread(target=self._update, daemon=True)
        self.thread.start()
        
    def open_source(self, index):
        # Interpret digits as local camera indexes
        if isinstance(index, str) and index.isdigit():
            index = int(index)
        elif isinstance(index, str):
            if not index.startswith('http'):
                index = 'http://' + index
                
        self.index = index
        if isinstance(self.index, str):
            # Network camera with FFMPEG
            self.video = cv2.VideoCapture(self.index, cv2.CAP_FFMPEG)
            # Reduce buffer size to minimize delay (works on some FFMPEG configs)
            self.video.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        else:
            # Local Camera with DirectShow to avoid MSMF hardware errors on Windows
            self.video = cv2.VideoCapture(self.index, cv2.CAP_DSHOW)
            self.video.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.video.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            
    def _update(self):
        """Continuously reads frames to keep the buffer empty."""
        while self.running:
            if hasattr(self, 'video') and self.video.isOpened():
                success, frame = self.video.read()
                if success:
                    with self.lock:
                        self.success = success
                        self.frame = frame.copy()
                else:
                    time.sleep(0.01)
            else:
                time.sleep(0.1)

    def __del__(self):
        self.running = False
        if hasattr(self, 'video') and self.video.isOpened():
            self.video.release()

    def get_frame(self):
        # We always return the freshest frame pulled by the background thread!
        with self.lock:
            if self.frame is None:
                return None, False
            return self.frame.copy(), self.success

    def change_source(self, index):
        with self.lock:
            if hasattr(self, 'video') and self.video.isOpened():
                self.video.release()
            
            # Reset current frame
            self.frame = None
            self.success = False
            
            self.open_source(index)
            return self.video.isOpened()
