// Face Recognition Attendance System - ENHANCED WITH YOUR NEW ELEVENLABS API
// Website displays English - AI Voice speaks Hindi with YOUR credentials
class AttendanceSystem {
    constructor() {
        this.webcam = document.getElementById('webcam');
        this.canvas = document.getElementById('canvas');
        this.webcamStatus = document.getElementById('webcamStatus');
        this.attendanceStatus = document.getElementById('attendanceStatus');
        this.isProcessing = false;
        this.currentUser = null;
        
        // 🔥 YOUR NEW ELEVENLABS CREDENTIALS INTEGRATED
        this.hindiVoiceEnabled = true;
        this.elevenLabsApiKey = 'sk_11de27c9cee94fe617e3f768b6124bc857dea2a18f1c8af4';  // 🔥 YOUR NEW API KEY
        this.hindiVoiceId = 'H6QPv2pQZDcGqLwDTIJQ';  // Your voice ID (Kanishka)
        
        console.log('🚀 AttendanceSystem initializing with YOUR NEW ElevenLabs voice...');
        this.init();
    }

    async init() {
        try {
            await this.startWebcam();
            // Initialize Hindi voice system with YOUR credentials
            this.initializeHindiVoiceSystem();
            
            // Wait 2 seconds before starting detection
            setTimeout(() => {
                this.startFaceDetection();
            }, 2000);
        } catch (error) {
            console.error('❌ Error initializing camera:', error);
            this.updateWebcamStatus('Camera access denied or not available');
            this.updateAttendanceStatus('error', '❌ Camera not accessible');
        }
    }

    initializeHindiVoiceSystem() {
        console.log('🎵 Initializing YOUR ElevenLabs Hindi voice system...');
        console.log('🔑 Using API Key:', this.elevenLabsApiKey.substring(0, 20) + '...');
        console.log('🎤 Using Voice ID:', this.hindiVoiceId);
        
        // Test browser Hindi voice support as fallback
        if ('speechSynthesis' in window) {
            speechSynthesis.getVoices();
            speechSynthesis.onvoiceschanged = () => {
                const voices = speechSynthesis.getVoices();
                const hindiVoice = voices.find(voice => 
                    voice.lang.startsWith('hi') || 
                    voice.name.toLowerCase().includes('hindi') ||
                    voice.name.toLowerCase().includes('bharati')
                );
                
                if (hindiVoice) {
                    console.log('✅ Browser Hindi voice found:', hindiVoice.name);
                    this.browserHindiVoice = hindiVoice;
                } else {
                    console.log('⚠️ No browser Hindi voice found, will use default');
                }
            };
        }
        
        console.log('🎵 YOUR ElevenLabs Hindi voice system ready!');
    }

    async startWebcam() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    width: { ideal: 640 },
                    height: { ideal: 480 },
                    facingMode: 'user'
                }
            });
            
            this.webcam.srcObject = stream;
            this.updateWebcamStatus('Camera ready - Looking for faces...');
            console.log('✅ Webcam started successfully');
        } catch (error) {
            throw new Error('Unable to access camera: ' + error.message);
        }
    }

    startFaceDetection() {
        console.log('🔍 Starting face detection...');
        
        setInterval(() => {
            if (!this.isProcessing && this.webcam.readyState === this.webcam.HAVE_ENOUGH_DATA) {
                this.detectFace();
            }
        }, 4000);
    }

    async detectFace() {
        console.log('📸 Detecting face...');
        
        this.clearForm();
        this.currentUser = null;
        
        const imageData = this.captureFrame();
        
        if (imageData) {
            this.updateWebcamStatus('Face detected - Identifying...');
            this.updateAttendanceStatus('processing', '🔄 Identifying person...');
            this.isProcessing = true;
            
            try {
                const result = await this.recognizeFace(imageData);
                console.log('🎯 Recognition result:', result);
                this.handleRecognitionResult(result);
            } catch (error) {
                console.error('❌ Recognition error:', error);
                this.updateWebcamStatus('Recognition error - Please try again');
                this.updateAttendanceStatus('error', '❌ System error occurred');
            } finally {
                setTimeout(() => {
                    this.isProcessing = false;
                    if (!this.currentUser) {
                        this.updateWebcamStatus('Looking for faces...');
                        this.updateAttendanceStatus('', 'Ready to scan face');
                    }
                }, 8000);
            }
        }
    }

    captureFrame() {
        try {
            if (this.webcam.videoWidth === 0 || this.webcam.videoHeight === 0) {
                console.log('⚠️ Webcam not ready yet');
                return null;
            }
            
            this.canvas.width = this.webcam.videoWidth;
            this.canvas.height = this.webcam.videoHeight;
            
            const context = this.canvas.getContext('2d');
            context.drawImage(this.webcam, 0, 0);
            
            return this.canvas.toDataURL('image/jpeg', 0.8);
        } catch (error) {
            console.error('❌ Error capturing frame:', error);
            return null;
        }
    }

    async recognizeFace(imageData) {
        const csrfToken = this.getCsrfToken();
        console.log('📤 Sending recognition request...');
        
        const response = await fetch('/attendance/api/recognize_face/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({
                image: imageData
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        return await response.json();
    }

    handleRecognitionResult(result) {
        if (result.success && result.user_data) {
            console.log('✅ Person recognized:', result.user_data.name);
            
            this.currentUser = result.user_data;
            this.fillUserForm(result.user_data);
            this.markAttendance(result.user_data, result.session_info);
            
        } else {
            console.log('❌ Recognition failed:', result.message);
            this.handleError(result);
        }
    }

    fillUserForm(userData) {
        console.log('📝 Filling form for user:', userData.name);
        
        this.clearForm();
        
        document.getElementById('userName').value = userData.name || '';
        document.getElementById('userEmail').value = userData.email || '';
        document.getElementById('userCity').value = userData.city || '';
        document.getElementById('userShivir').value = userData.shivir_level || '';
        document.getElementById('userStatus').value = userData.status || '';
        document.getElementById('sessionInfo').value = userData.current_session || '';
        
        console.log('✅ Form filled successfully for:', userData.name);
    }

    // 🔥 ENHANCED ATTENDANCE MARKING WITH YOUR ELEVENLABS HINDI VOICE
    async markAttendance(userData, sessionInfo) {
        console.log('📋 Marking attendance for:', userData.name);
        
        try {
            const csrfToken = this.getCsrfToken();
            const sessionType = sessionInfo?.type || 'MA';
            
            console.log('📋 Attendance request:', {
                email: userData.email,
                shivir: sessionType
            });
            
            const response = await fetch('/api/mark_attendance/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({
                    email: userData.email,
                    shivir: sessionType
                })
            });

            const result = await response.json();
            console.log('📋 Attendance response:', result);
            
            if (response.ok && result.success) {
                // 🎉 SUCCESS - English display + YOUR Hindi voice
                this.updateWebcamStatus(`Welcome ${userData.name}! Attendance marked.`);
                this.updateAttendanceStatus('success', '✅ Attendance Recorded Successfully!');
                
                // 🔥 PLAY YOUR ELEVENLABS HINDI VOICE MESSAGE
                const hindiMessage = result.hindi_voice_message || result.voice_message;
                if (hindiMessage) {
                    this.playYourElevenLabsHindi(hindiMessage);
                }
                
                setTimeout(() => {
                    this.resetAfterSuccess();
                }, 10000);
                
            } else {
                // Handle errors with YOUR Hindi voice
                this.handleAttendanceErrorWithHindi(result, userData);
            }
            
        } catch (error) {
            console.error('❌ Attendance marking error:', error);
            this.updateWebcamStatus('Attendance marking failed');
            this.updateAttendanceStatus('error', '❌ Failed to mark attendance');
            
            // Play system error in Hindi with YOUR voice
            this.playYourElevenLabsHindi('सिस्टम में कुछ समस्या है। कृपया दोबारा कोशिश करें, धन्यवाद।');
        }
    }

    // 🔥 HANDLE ATTENDANCE ERRORS WITH YOUR HINDI VOICE
    handleAttendanceErrorWithHindi(result, userData) {
        console.log('🚨 Handling attendance error with YOUR Hindi voice:', result.error);
        
        // Display English message on website
        if (result.error && result.error.includes('already marked')) {
            this.updateWebcamStatus(`${userData.name} already attended today`);
            this.updateAttendanceStatus('duplicate', '⚠️ Already attended today');
        } else if (result.error && result.error.includes('blacklisted')) {
            this.updateWebcamStatus('Access denied - Blacklisted');
            this.updateAttendanceStatus('error', '🚫 Access denied - Contact admin');
        } else if (result.error && result.error.includes('inactive')) {
            this.updateWebcamStatus('Account inactive');
            this.updateAttendanceStatus('error', '⚠️ Account inactive - Contact admin');
        } else {
            this.updateWebcamStatus('Cannot mark attendance');
            this.updateAttendanceStatus('error', '❌ Cannot mark attendance');
        }
        
        // 🔥 PLAY YOUR ELEVENLABS HINDI VOICE MESSAGE FROM BACKEND
        const hindiMessage = result.hindi_voice_message;
        if (hindiMessage) {
            this.playYourElevenLabsHindi(hindiMessage);
        }
    }

    // 🔥 HANDLE RECOGNITION ERRORS WITH YOUR HINDI VOICE  
    handleError(result) {
        console.log('🚨 Handling recognition error:', result.error_type);
        
        // Default Hindi messages for recognition errors
        let hindiMessage = 'माफ़ करें, कुछ समस्या हुई है। कृपया दोबारा कोशिश करें, धन्यवाद।';
        
        switch (result.error_type) {
            case 'face_not_found':
                this.updateWebcamStatus('No clear face detected');
                this.updateAttendanceStatus('error', '❌ No face detected');
                hindiMessage = 'कृपया अपना चेहरा कैमरे के सामने स्पष्ट रूप से दिखाएं, धन्यवाद।';
                break;
                
            case 'person_not_recognized':
                this.updateWebcamStatus('Face not recognized');
                this.updateAttendanceStatus('error', '❓ Unknown person - Please register');
                hindiMessage = 'माफ़ करें, आपकी पहचान नहीं हो सकी। कृपया पहले अपना पंजीकरण कराएं, धन्यवाद।';
                break;
                
            case 'person_inactive':
                if (result.user_data) {
                    this.currentUser = result.user_data;
                    this.fillUserForm(result.user_data);
                    hindiMessage = result.hindi_voice_message || `हैप्पी थॉट्स ${result.user_data.name}, आप वर्तमान में निष्क्रिय हैं। कृपया एडमिन से संपर्क करें, धन्यवाद।`;
                }
                this.updateWebcamStatus('Account inactive');
                this.updateAttendanceStatus('error', '⚠️ Account inactive - Contact admin');
                break;
                
            case 'person_blacklisted':
                if (result.user_data) {
                    this.currentUser = result.user_data;
                    this.fillUserForm(result.user_data);
                    hindiMessage = result.hindi_voice_message || `हैप्पी थॉट्स ${result.user_data.name}, आप वर्तमान में प्रतिबंधित सूची में हैं। कृपया एडमिन से संपर्क करें, धन्यवाद।`;
                }
                this.updateWebcamStatus('Access denied');
                this.updateAttendanceStatus('error', '🚫 Access denied - Contact admin');
                break;
                
            case 'no_active_session':
                if (result.user_data) {
                    this.currentUser = result.user_data;
                    this.fillUserForm(result.user_data);
                    hindiMessage = result.hindi_voice_message || `हैप्पी थॉट्स ${result.user_data.name}, वर्तमान में कोई सक्रिय सत्र नहीं है। कृपया एडमिन से संपर्क करें, धन्यवाद।`;
                }
                this.updateWebcamStatus('No active session');
                this.updateAttendanceStatus('error', '⚠️ No active session - Contact admin');
                break;
                
            default:
                this.updateWebcamStatus('Recognition error occurred');
                this.updateAttendanceStatus('error', '❌ System error');
        }
        
        // 🔥 PLAY YOUR ELEVENLABS HINDI ERROR MESSAGE
        this.playYourElevenLabsHindi(hindiMessage);
    }

    // 🔥 YOUR MAIN ELEVENLABS HINDI VOICE FUNCTION
    async playYourElevenLabsHindi(hindiText) {
        if (!this.hindiVoiceEnabled || !hindiText) {
            console.log('⚠️ Hindi voice disabled or no text provided');
            return;
        }

        console.log('🔊 Playing YOUR ElevenLabs Hindi voice:', hindiText);

        // Method 1: Try YOUR ElevenLabs API for high-quality Hindi voice
        const elevenLabsSuccess = await this.callYourElevenLabsAPI(hindiText);
        
        // Method 2: Fallback to browser speech synthesis if YOUR API fails
        if (!elevenLabsSuccess) {
            setTimeout(() => {
                this.playBrowserHindiTTS(hindiText);
            }, 500);
        }
    }

    // 🔥 YOUR ELEVENLABS API INTEGRATION (HIGH QUALITY)
    async callYourElevenLabsAPI(hindiText) {
        try {
            console.log('🎵 Calling YOUR ElevenLabs API...');
            console.log('🔑 Using YOUR API Key:', this.elevenLabsApiKey.substring(0, 20) + '...');
            console.log('🎤 Using YOUR Voice ID:', this.hindiVoiceId);
            
            const response = await fetch(`https://api.elevenlabs.io/v1/text-to-speech/${this.hindiVoiceId}`, {
                method: 'POST',
                headers: {
                    'Accept': 'audio/mpeg',
                    'Content-Type': 'application/json',
                    'xi-api-key': this.elevenLabsApiKey  // 🔥 YOUR API KEY
                },
                body: JSON.stringify({
                    text: hindiText,
                    model_id: "eleven_multilingual_v2",  // Best for Hindi
                    voice_settings: {
                        stability: 0.85,
                        similarity_boost: 0.90,
                        style: 1.0,
                        use_speaker_boost: true
                    }
                })
            });

            if (response.ok) {
                const audioBlob = await response.blob();
                const audioUrl = URL.createObjectURL(audioBlob);
                const audio = new Audio(audioUrl);
                
                audio.onended = () => {
                    URL.revokeObjectURL(audioUrl);  // Clean up memory
                };
                
                audio.onloadeddata = () => {
                    console.log('🎵 Audio loaded successfully');
                };
                
                await audio.play();
                console.log('✅ YOUR ElevenLabs Hindi voice played successfully!');
                return true;
            } else {
                const errorText = await response.text();
                console.log('⚠️ YOUR ElevenLabs API failed:', response.status, errorText);
                return false;
            }
        } catch (error) {
            console.log('⚠️ YOUR ElevenLabs API error:', error.message);
            return false;
        }
    }

    // 🔥 BROWSER HINDI TTS (FALLBACK)
    playBrowserHindiTTS(hindiText) {
        console.log('🗣️ Using browser Hindi TTS fallback...');
        
        if ('speechSynthesis' in window) {
            // Cancel any ongoing speech
            speechSynthesis.cancel();
            
            const utterance = new SpeechSynthesisUtterance(hindiText);
            
            // Configure for Hindi
            utterance.lang = 'hi-IN';
            utterance.rate = 0.8;
            utterance.pitch = 1.0;
            utterance.volume = 0.8;
            
            // Use Hindi voice if available
            if (this.browserHindiVoice) {
                utterance.voice = this.browserHindiVoice;
                console.log('🗣️ Using browser Hindi voice:', this.browserHindiVoice.name);
            } else {
                console.log('🗣️ Using default voice with Hindi lang setting');
            }
            
            utterance.onstart = () => {
                console.log('🔊 Browser TTS started');
            };
            
            utterance.onend = () => {
                console.log('✅ Browser Hindi TTS completed');
            };
            
            utterance.onerror = (event) => {
                console.log('❌ Browser TTS error:', event.error);
            };
            
            speechSynthesis.speak(utterance);
        } else {
            console.log('❌ Speech synthesis not supported');
        }
    }

    // 🔥 UTILITY FUNCTIONS (UNCHANGED)
    clearForm() {
        document.getElementById('userName').value = '';
        document.getElementById('userEmail').value = '';
        document.getElementById('userCity').value = '';
        document.getElementById('userShivir').value = '';
        document.getElementById('userStatus').value = '';
        document.getElementById('sessionInfo').value = '';
    }

    resetAfterSuccess() {
        this.currentUser = null;
        this.clearForm();
        this.updateWebcamStatus('Looking for faces...');
        this.updateAttendanceStatus('', 'Ready to scan face');
        console.log('🔄 System reset after successful attendance');
    }

    updateWebcamStatus(message) {
        this.webcamStatus.textContent = message;
        console.log('📺 Webcam status:', message);
    }

    updateAttendanceStatus(type, message) {
        this.attendanceStatus.className = `attendance-status ${type}`;
        this.attendanceStatus.querySelector('.status-message').textContent = message;
        console.log('📊 Attendance status:', type, message);
    }

    // 🔥 LEGACY VOICE FUNCTION (KEPT FOR COMPATIBILITY)
    playVoiceAnnouncement(message) {
        console.log('🔊 Legacy voice (English):', message);
        
        if (message && 'speechSynthesis' in window) {
            const utterance = new SpeechSynthesisUtterance(message);
            utterance.rate = 0.8;
            utterance.pitch = 1;
            utterance.volume = 0.8;
            utterance.lang = 'en-US';
            speechSynthesis.speak(utterance);
        }
    }

    getCsrfToken() {
        const name = 'csrftoken';
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue || '';
    }
}

// Initialize the attendance system when page loads
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Initializing Face Recognition Attendance System with YOUR ElevenLabs Hindi Voice...');
    new AttendanceSystem();
});
