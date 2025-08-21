class VuGruMusicApp {
    constructor() {
        this.abortController = null;
        this.currentTrack = null;
        this.recentTracks = [];
        this.user = null;
        this.token = null;
        
        // Check authentication first - be more explicit about this
        this.token = localStorage.getItem('authToken');
        this.user = this.parseUserFromStorage();
        
        // If not authenticated, redirect immediately
        if (!this.token || !this.user) {
            this.redirectToLogin();
            return; // Stop execution here
        }
        
        // Only initialize if authenticated
        this.initializeApp();
        this.loadSettings();
        this.loadRecentTracks();
        this.setupUserInterface();
    }

    parseUserFromStorage() {
        try {
            const userStr = localStorage.getItem('user');
            return userStr ? JSON.parse(userStr) : null;
        } catch (error) {
            console.warn('Failed to parse user from localStorage:', error);
            return null;
        }
    }

    redirectToLogin() {
        // Clear any invalid auth data
        localStorage.removeItem('authToken');
        localStorage.removeItem('user');
        
        // Redirect to login page
        window.location.replace('/static/login.html');
    }

    isAuthenticated() {
        return !!(this.token && this.user);
    }

    getAuthHeaders() {
        return this.token ? {
            'Authorization': `Bearer ${this.token}`
        } : {};
    }

    setupUserInterface() {
        console.log('Setting up user interface, user:', this.user);
        
        // Try to add to navigation first
        const userControls = document.getElementById('userControls');
        
        if (userControls && this.user) {
            // Clear any existing content
            userControls.innerHTML = '';
            
            // Create user avatar with first letter of name or email
            const avatar = document.createElement('div');
            avatar.className = 'user-avatar';
            const displayName = this.user.full_name || this.user.email;
            avatar.textContent = displayName.charAt(0).toUpperCase();
            
            // Create user name display
            const userName = document.createElement('span');
            userName.className = 'user-name';
            userName.textContent = this.user.full_name || this.user.email;
            
            // Create logout button
            const logoutBtn = document.createElement('button');
            logoutBtn.className = 'logout-btn';
            logoutBtn.textContent = 'Sign Out';
            logoutBtn.addEventListener('click', () => this.logout());
            
            userControls.appendChild(avatar);
            userControls.appendChild(userName);
            userControls.appendChild(logoutBtn);
            
            console.log('User interface elements added to navigation');
        }
        
    }

    logout() {
        // Clear local storage
        localStorage.removeItem('authToken');
        localStorage.removeItem('user');
        
        // Redirect to login
        window.location.href = '/static/login.html';
    }

    initializeApp() {
        // Get DOM elements
        this.form = document.getElementById('musicForm');
        this.generateBtn = document.getElementById('generateBtn');
        this.stopBtn = document.getElementById('stopBtn');
        this.statusMessage = document.getElementById('statusMessage');
        this.resultsSection = document.getElementById('resultsSection');
        this.audioPlayer = document.getElementById('audioPlayer');
        this.downloadBtn = document.getElementById('downloadBtn');
        this.promptText = document.getElementById('promptText');
        this.recentTracksSection = document.getElementById('recentTracks');
        this.tracksList = document.getElementById('tracksList');
        this.presetSelect = document.getElementById('presetSelect');
        this.musicPrompt = document.getElementById('musicPrompt');

        // Bind event listeners
        this.form.addEventListener('submit', (e) => this.handleSubmit(e));
        this.stopBtn.addEventListener('click', () => this.handleStop());
        this.downloadBtn.addEventListener('click', () => this.handleDownload());
        this.presetSelect.addEventListener('change', () => this.handlePresetChange());

        // Save settings on input change
        this.form.addEventListener('input', () => this.saveSettings());
        this.form.addEventListener('change', () => this.saveSettings());
    }

    loadSettings() {
        try {
            const saved = localStorage.getItem('vugru-settings');
            if (saved) {
                const settings = JSON.parse(saved);
                
                // Restore form values
                Object.keys(settings).forEach(key => {
                    const element = document.querySelector(`[name="${key}"]`);
                    if (element) {
                        if (element.type === 'radio') {
                            const radio = document.querySelector(`[name="${key}"][value="${settings[key]}"]`);
                            if (radio) radio.checked = true;
                        } else {
                            element.value = settings[key];
                        }
                    }
                });
            }
        } catch (error) {
            console.warn('Could not load saved settings:', error);
        }
    }

    saveSettings() {
        try {
            const formData = new FormData(this.form);
            const settings = {};
            
            for (const [key, value] of formData.entries()) {
                settings[key] = value;
            }
            
            localStorage.setItem('vugru-settings', JSON.stringify(settings));
        } catch (error) {
            console.warn('Could not save settings:', error);
        }
    }

    async loadRecentTracks() {
        try {
            const response = await fetch('/api/recent_tracks', {
                headers: this.getAuthHeaders()
            });
            if (response.ok) {
                const data = await response.json();
                this.recentTracks = data.tracks || [];
                this.updateRecentTracksDisplay();
            }
        } catch (error) {
            console.warn('Could not load recent tracks:', error);
        }
    }

    updateRecentTracksDisplay() {
        if (this.recentTracks.length === 0) {
            this.recentTracksSection.style.display = 'none';
            return;
        }

        this.recentTracksSection.style.display = 'block';
        
        const html = this.recentTracks.map(track => `
            <div class="track-item">
                <div class="track-info">
                    <div class="track-name">${this.escapeHtml(track.filename)}</div>
                    <div class="track-details">${track.duration}s • ${track.prompt}</div>
                </div>
                <div class="track-actions">
                    <button class="btn btn-small" onclick="app.playTrack('${track.id}')">Play</button>
                    <button class="btn btn-small" onclick="app.downloadTrack('${track.id}', '${track.filename}')">Download</button>
                </div>
            </div>
        `).join('');
        
        this.tracksList.innerHTML = html;
    }

    async handleSubmit(event) {
        event.preventDefault();
        
        if (this.abortController) {
            this.showStatus('A generation is already in progress', 'warning');
            return;
        }

        // Disable generate button and show loading
        this.generateBtn.disabled = true;
        this.stopBtn.style.display = 'inline-block';
        this.resultsSection.style.display = 'none';
        
        const btnText = this.generateBtn.querySelector('.btn-text');
        const spinner = this.generateBtn.querySelector('.loading-spinner');
        btnText.style.display = 'none';
        spinner.style.display = 'inline';

        this.showStatus('Generating your custom music track...', 'info');

        // Create abort controller
        this.abortController = new AbortController();

        try {
            // Collect form data
            const formData = new FormData(this.form);
            const requestData = {
                prompt: formData.get('musicPrompt'),
                duration: parseInt(formData.get('duration')),
                vocals_mode: 'instrumental'
            };

            // Make API request
            const response = await fetch('/api/generate_music', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...this.getAuthHeaders()
                },
                body: JSON.stringify(requestData),
                signal: this.abortController.signal
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: 'Unknown error occurred' }));
                
                // Check for quota error (402 status)
                if (response.status === 402) {
                    throw new Error(errorData.detail || 'Not enough credits for this request');
                }
                
                throw new Error(errorData.detail || `HTTP ${response.status}`);
            }

            // Get the response as blob for audio
            const audioBlob = await response.blob();
            const audioUrl = URL.createObjectURL(audioBlob);
            
            // Get additional info from headers
            const trackId = response.headers.get('X-Track-ID');
            const prompt = response.headers.get('X-Prompt');
            const filename = this.getFilenameFromHeaders(response.headers) || 'vugru-track.mp3';

            // Store current track info
            this.currentTrack = {
                url: audioUrl,
                blob: audioBlob,
                filename: filename,
                id: trackId
            };

            // Display results
            this.audioPlayer.src = audioUrl;
            this.promptText.textContent = prompt || 'Prompt not available';
            this.resultsSection.style.display = 'block';
            
            this.showStatus('✅ Music generated successfully!', 'success');
            
            // Refresh recent tracks and user library
            await this.loadRecentTracks();
            await this.loadUserLibrary();

        } catch (error) {
            if (error.name === 'AbortError') {
                this.showStatus('Generation cancelled', 'info');
            } else {
                console.error('Generation error:', error);
                this.showStatus(`❌ ${error.message}`, 'error');
            }
        } finally {
            // Reset UI
            this.generateBtn.disabled = false;
            this.stopBtn.style.display = 'none';
            btnText.style.display = 'inline';
            spinner.style.display = 'none';
            this.abortController = null;
        }
    }

    handleStop() {
        if (this.abortController) {
            this.abortController.abort();
            this.showStatus('Stopping generation...', 'info');
        }
    }

    handleDownload() {
        if (!this.currentTrack) return;

        const link = document.createElement('a');
        link.href = this.currentTrack.url;
        link.download = this.currentTrack.filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    async playTrack(trackId) {
        try {
            const response = await fetch(`/api/track/${trackId}`);
            if (!response.ok) {
                throw new Error('Track not found or expired');
            }
            
            const audioBlob = await response.blob();
            const audioUrl = URL.createObjectURL(audioBlob);
            
            this.audioPlayer.src = audioUrl;
            this.audioPlayer.play();
            
            // Clean up old URL if exists
            if (this.currentTrack?.url) {
                URL.revokeObjectURL(this.currentTrack.url);
            }
            
            this.currentTrack = {
                url: audioUrl,
                blob: audioBlob,
                filename: this.getFilenameFromHeaders(response.headers) || 'track.mp3'
            };
            
            this.resultsSection.style.display = 'block';
            
        } catch (error) {
            this.showStatus(`❌ Could not play track: ${error.message}`, 'error');
        }
    }

    async downloadTrack(trackId, filename) {
        try {
            const response = await fetch(`/api/track/${trackId}`);
            if (!response.ok) {
                throw new Error('Track not found or expired');
            }
            
            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            
            const link = document.createElement('a');
            link.href = url;
            link.download = filename;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            URL.revokeObjectURL(url);
            
        } catch (error) {
            this.showStatus(`❌ Could not download track: ${error.message}`, 'error');
        }
    }

    showStatus(message, type = 'info') {
        this.statusMessage.textContent = message;
        this.statusMessage.className = `status-message status-${type}`;
        this.statusMessage.style.display = 'block';
        
        // Auto-hide success and info messages after 5 seconds
        if (type === 'success' || type === 'info') {
            setTimeout(() => {
                this.statusMessage.style.display = 'none';
            }, 5000);
        }
    }

    getFilenameFromHeaders(headers) {
        const disposition = headers.get('Content-Disposition');
        if (disposition) {
            const matches = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/.exec(disposition);
            if (matches != null && matches[1]) {
                return matches[1].replace(/['"]/g, '');
            }
        }
        return null;
    }

    handlePresetChange() {
        const preset = this.presetSelect.value;
        
        const presets = {
            luxury: "Create elegant, sophisticated background music for luxury real estate videos. Use orchestral strings, gentle piano, and subtle atmospheric elements. Keep it refined and upscale with a sense of grandeur and exclusivity.",
            modern: "Create modern, upbeat background music for contemporary real estate videos. Use clean electronic elements, light percussion, and bright synths. Make it energetic but professional with a fresh, forward-thinking vibe.",
            warm: "Create warm, inviting background music for family-friendly real estate videos. Use acoustic instruments like guitar and piano with soft strings. Make it cozy, welcoming, and emotionally appealing with a homey feeling.",
            corporate: "Create clean, professional background music for commercial real estate videos. Use minimal instrumentation with subtle corporate elements. Keep it polished, trustworthy, and business-appropriate with steady rhythm.",
            rustic: "Create rustic, acoustic background music for country or cabin real estate videos. Use acoustic guitar, banjo, and natural sounds. Make it folksy, down-to-earth, and connected to nature with organic textures.",
            cinematic: "Create cinematic, dramatic background music for high-end real estate videos. Use full orchestration with building dynamics and emotional swells. Make it epic and inspiring with movie-like production value."
        };
        
        if (preset && presets[preset]) {
            this.musicPrompt.value = presets[preset];
            // Trigger save settings
            this.saveSettings();
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    async loadUserLibrary() {
        try {
            const token = localStorage.getItem('authToken');
            if (!token) {
                document.getElementById('musicLibrary').style.display = 'none';
                return;
            }
            
            const response = await fetch('/api/user_tracks', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            
            const libraryContent = document.getElementById('libraryContent');
            
            if (!response.ok) {
                if (response.status === 401) {
                    libraryContent.innerHTML = '<p style="text-align: center; color: #6b7280;">Please log in to view your music library</p>';
                } else {
                    libraryContent.innerHTML = '<p style="text-align: center; color: #ef4444;">Failed to load music library</p>';
                }
                return;
            }
            
            const tracks = await response.json();
            
            if (!tracks || tracks.length === 0) {
                libraryContent.innerHTML = '<p style="text-align: center; color: #6b7280;">No saved tracks yet. Generate your first track above!</p>';
                return;
            }
            
            // Display user's tracks
            libraryContent.innerHTML = `
                <div class="tracks-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 16px;">
                    ${tracks.map(track => `
                        <div class="library-track-card" style="border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px; background: white;">
                            <h4 style="margin: 0 0 8px 0; font-size: 16px; font-weight: 600;">${this.escapeHtml(track.title)}</h4>
                            <p style="color: #6b7280; font-size: 14px; margin: 0 0 8px 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${this.escapeHtml(track.prompt)}</p>
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 12px;">
                                <small style="color: #9ca3af;">
                                    ${track.duration}s • ${new Date(track.created_at).toLocaleDateString()}
                                </small>
                                <div style="display: flex; gap: 8px;">
                                    <button onclick="app.playLibraryTrack('${track.file_url}', '${this.escapeHtml(track.title).replace(/'/g, "\\'")}')" 
                                            class="btn btn-small" style="padding: 4px 12px; font-size: 14px;">
                                        ▶ Play
                                    </button>
                                    <button onclick="app.downloadLibraryTrack('${track.file_url}', '${track.file_name}')" 
                                            class="btn btn-small btn-success" style="padding: 4px 12px; font-size: 14px;">
                                        ⬇ Download
                                    </button>
                                    <button onclick="app.deleteLibraryTrack('${track.id}')" 
                                            class="btn btn-small" style="padding: 4px 12px; font-size: 14px; background: #ef4444;">
                                        🗑 Delete
                                    </button>
                                </div>
                            </div>
                        </div>
                    `).join('')}
                </div>
            `;
            
        } catch (error) {
            console.error('Error loading user library:', error);
            document.getElementById('libraryContent').innerHTML = '<p style="text-align: center; color: #ef4444;">Error loading music library</p>';
        }
    }
    
    async playLibraryTrack(fileUrl, title) {
        try {
            // For now, we'll use the file URL directly
            // In production, you might want to get a signed URL from the backend
            this.audioPlayer.src = fileUrl;
            this.audioPlayer.play();
            this.resultsSection.style.display = 'block';
            this.promptDisplay.textContent = title;
            
        } catch (error) {
            this.showStatus(`❌ Could not play track: ${error.message}`, 'error');
        }
    }
    
    async downloadLibraryTrack(fileUrl, filename) {
        try {
            // Create a download link
            const link = document.createElement('a');
            link.href = fileUrl;
            link.download = filename;
            link.target = '_blank';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
        } catch (error) {
            this.showStatus(`❌ Could not download track: ${error.message}`, 'error');
        }
    }
    
    async deleteLibraryTrack(trackId) {
        if (!confirm('Are you sure you want to delete this track?')) {
            return;
        }
        
        try {
            const token = localStorage.getItem('authToken');
            const response = await fetch(`/api/user_tracks/${trackId}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            
            if (!response.ok) {
                throw new Error('Failed to delete track');
            }
            
            this.showStatus('✅ Track deleted successfully', 'success');
            // Reload the library
            await this.loadUserLibrary();
            
        } catch (error) {
            this.showStatus(`❌ Could not delete track: ${error.message}`, 'error');
        }
    }

    // Cleanup method
    destroy() {
        if (this.currentTrack?.url) {
            URL.revokeObjectURL(this.currentTrack.url);
        }
        if (this.abortController) {
            this.abortController.abort();
        }
    }
}

// Initialize the app when the page loads
let app;
document.addEventListener('DOMContentLoaded', () => {
    try {
        app = new VuGruMusicApp();
        // Load user's music library
        app.loadUserLibrary();
    } catch (error) {
        console.error('Failed to initialize app:', error);
        // Fallback: redirect to login if app fails to initialize
        window.location.replace('/static/login.html');
    }
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (app) {
        app.destroy();
    }
});
