class FaceDashboard {
    constructor() {
        this.statusIndicator = document.getElementById('status-indicator');
        this.statusText = document.getElementById('status-text');
        this.cameraSelect = document.getElementById('camera-select');
        this.eventsList = document.getElementById('events-list');
        this.enrollForm = document.getElementById('enroll-form');
        this.enrollBtn = document.getElementById('enroll-btn');
        this.enrollStatus = document.getElementById('enroll-status');
        this.galleryGrid = document.getElementById('gallery-grid');
        this.enrolledCount = document.getElementById('enrolled-count');
        
        this.overlay = document.getElementById('latest-recognition');
        this.overlayName = document.getElementById('overlay-name');
        this.overlayConf = document.getElementById('overlay-conf');
        this.overlayBar = document.getElementById('overlay-bar');
        
        this.lastEventId = null;
        this.overlayTimeout = null;
        
        this.init();
    }

    init() {
        this.bindEvents();
        this.startPolling();
        this.fetchGallery();
    }

    bindEvents() {
        this.cameraSelect.addEventListener('change', (e) => {
            if (e.target.value === 'url') {
                const ipurl = prompt("Enter Mobile IP Camera Video URL (e.g., http://192.168.1.10:8080/video):");
                if (ipurl) {
                    this.changeCamera(ipurl);
                } else {
                    this.cameraSelect.value = "0";
                }
            } else {
                this.changeCamera(e.target.value);
            }
        });

        this.enrollForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.enrollPerson();
        });
    }

    startPolling() {
        // Poll status every 2 seconds
        setInterval(() => this.fetchStatus(), 2000);
        // Poll events every 1 second
        setInterval(() => this.fetchEvents(), 1000);
        
        this.fetchStatus();
        this.fetchEvents();
    }

    async fetchStatus() {
        try {
            const res = await fetch('/api/status');
            const data = await res.json();
            
            if (data.status === 'online') {
                this.statusIndicator.className = 'status-indicator online';
                this.statusText.textContent = data.camera_active ? 'System Active' : 'Camera Error';
            }
        } catch (err) {
            this.statusIndicator.className = 'status-indicator';
            this.statusText.textContent = 'Server Offline';
        }
    }

    async fetchEvents() {
        try {
            const res = await fetch('/api/events?limit=20');
            const events = await res.json();
            
            if (events.length === 0) return;
            
            // Check if there's a new event
            const latest = events[0];
            const latestId = latest.name + latest.timestamp; // rough unique ID
            
            if (this.lastEventId !== latestId) {
                this.lastEventId = latestId;
                this.renderEvents(events);
                
                // Show overlay for new recognition
                if (latest.name !== 'Unknown') {
                    this.showOverlay(latest.name, latest.confidence);
                }
            }
        } catch (err) {
            console.error('Error fetching events:', err);
        }
    }

    renderEvents(events) {
        this.eventsList.innerHTML = '';
        events.forEach(ev => {
            const div = document.createElement('div');
            div.className = 'event-card';
            
            const time = new Date(ev.timestamp).toLocaleTimeString();
            const conf = ev.confidence ? `${(ev.confidence * 100).toFixed(1)}%` : '--';
            const color = ev.name === 'Unknown' ? 'var(--danger)' : 'var(--accent)';
            
            div.innerHTML = `
                <div class="event-info">
                    <h4>${ev.name}</h4>
                    <p>${time}</p>
                </div>
                <div class="event-conf" style="color: ${color}; background: ${color}15">
                    ${conf}
                </div>
            `;
            this.eventsList.appendChild(div);
        });
    }

    showOverlay(name, confidence) {
        this.overlayName.textContent = name;
        const confPercent = Math.round(confidence * 100);
        this.overlayConf.textContent = `${confPercent}%`;
        
        this.overlay.style.display = 'block';
        
        // Reflow for animation
        void this.overlay.offsetWidth;
        this.overlayBar.style.width = `${confPercent}%`;
        
        clearTimeout(this.overlayTimeout);
        this.overlayTimeout = setTimeout(() => {
            this.overlay.style.display = 'none';
            this.overlayBar.style.width = '0%';
        }, 4000);
    }

    async fetchGallery() {
        try {
            const res = await fetch('/api/faces');
            const faces = await res.json();
            
            this.enrolledCount.textContent = `${faces.length} subject${faces.length !== 1 ? 's' : ''}`;
            this.galleryGrid.innerHTML = '';
            
            faces.forEach(face => {
                const div = document.createElement('div');
                div.className = 'gallery-item';
                
                // Using a generic avatar if we don't serve the raw files directly for security
                // In a prod app we'd serve the face images through a secure route
                div.innerHTML = `
                    <div style="position: relative">
                        <div class="gallery-img" style="background: var(--primary); display: flex; align-items:center; justify-content:center; font-size:1.5rem; font-weight:bold; color:white;">
                            ${face.name.charAt(0).toUpperCase()}
                        </div>
                        <button class="delete-btn" onclick="dashboard.deleteFace('${face.name.replace(/'/g, "\\'")}')">×</button>
                    </div>
                    <span class="gallery-name">${face.name.split(' ')[0]}</span>
                `;
                this.galleryGrid.appendChild(div);
            });
            
            if (faces.length === 0) {
                this.galleryGrid.innerHTML = '<div class="empty-state" style="grid-column: 1/-1">No enrolled faces</div>';
            }
        } catch (err) {
            console.error('Error fetching gallery:', err);
        }
    }

    async enrollPerson() {
        const nameInput = document.getElementById('person-name');
        const imageInput = document.getElementById('person-image');
        
        if (!nameInput.value || !imageInput.files[0]) return;
        
        this.enrollBtn.disabled = true;
        this.enrollBtn.innerHTML = '<div class="spinner" style="width:20px;height:20px;border-width:2px;"></div>';
        this.enrollStatus.textContent = '';
        
        const formData = new FormData();
        formData.append('name', nameInput.value);
        formData.append('image', imageInput.files[0]);
        
        try {
            const res = await fetch('/api/enroll', {
                method: 'POST',
                body: formData
            });
            
            const result = await res.json();
            
            if (result.status === 'success') {
                this.enrollStatus.style.color = 'var(--accent)';
                this.enrollStatus.textContent = 'Successfully enrolled!';
                this.enrollForm.reset();
                this.fetchGallery(); // Refresh gallery
            } else {
                this.enrollStatus.style.color = 'var(--danger)';
                this.enrollStatus.textContent = result.message || 'Enrollment failed.';
            }
        } catch (err) {
            this.enrollStatus.style.color = 'var(--danger)';
            this.enrollStatus.textContent = 'Network error during enrollment.';
        } finally {
            this.enrollBtn.disabled = false;
            this.enrollBtn.innerHTML = '<span>Enroll Person</span>';
        }
    }

    async deleteFace(name) {
        if (!confirm(`Are you sure you want to delete ${name}?`)) return;
        
        try {
            await fetch(`/api/faces/${encodeURIComponent(name)}`, { method: 'DELETE' });
            this.fetchGallery();
        } catch (err) {
            console.error('Error deleting face:', err);
        }
    }

    async changeCamera(index) {
        try {
            const res = await fetch('/api/camera', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ index: index })
            });
            const data = await res.json();
            if (data.status === 'error') {
                alert("Could not connect to camera.\n\nMake sure your phone is on the same Wi-Fi and you entered the exact video stream URL (e.g. it should end with /video or /mjpeg in IP Webcam apps).\n\nIf using IP Webcam, the URL is usually http://IP:8080/video");
                this.cameraSelect.value = "0"; // reset visually
                this.changeCamera(0); // switch back to default
            }
        } catch (err) {
            console.error('Error changing camera:', err);
        }
    }
}

// Initialize dashboard
const dashboard = new FaceDashboard();
