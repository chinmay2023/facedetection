// Face Recognition Attendance System - ENHANCED WITH ALL FACE_RECOGNIZE_LIVE.PY FEATURES
// Website displays English - AI Voice speaks Hindi with YOUR credentials
// 🚀 NEW: Smart Voice Repetition System + Session Day Progress + Advanced State Management
// 🔧 COMPLETELY FIXED: AI Voice & Error Display Issues Resolved + CLEAN SHIVIR DISPLAY

class AttendanceSystem {
    constructor() {
        this.webcam = document.getElementById('webcam');
        this.canvas = document.getElementById('canvas');
        this.webcamStatus = document.getElementById('webcamStatus');
        this.attendanceStatus = document.getElementById('attendanceStatus');
        this.isProcessing = false;
        this.currentUser = null;
        
        // 🔥 YOUR ELEVENLABS CREDENTIALS INTEGRATED
        this.hindiVoiceEnabled = true;
        this.elevenLabsApiKey = 'sk_11de27c9cee94fe617e3f768b6124bc857dea2a18f1c8af4';
        this.hindiVoiceId = 'H6QPv2pQZDcGqLwDTIJQ';
        
        // 🚀 NEW: Smart Voice Repetition System
        this.voiceSystem = {
            currentInterval: null,
            voiceCount: 0,
            currentMessage: '',
            currentMode: null,
            modes: {
                SUCCESS: 'success',           // 3 times then stop
                ALREADY_MARKED: 'already',    // 3 times then stop
                WAIT_NEXT_DAY: 'wait'        // Infinite until user leaves
            },
            maxRepeats: 3,
            repeatInterval: 3000  // 3 seconds
        };
        
        // 🚀 NEW: Message Cache System (like face_recognize_live.py)
        this.messageCache = {};
        this.MESSAGE_DISPLAY_SECONDS = 30;
        
        // 🔧 NEW: Audio Management to Fix Duplicate Voice Issue
        this.currentAudio = null;
        this.isVoicePlaying = false;
        this.audioQueue = [];
        
        console.log('🚀 Enhanced AttendanceSystem initializing with FIXED error handling...');
        this.init();
    }

    async init() {
        try {
            await this.startWebcam();
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

    // 🔧 NEW: Stop All Audio to Fix Duplicate Voice Issue
    stopAllAudio() {
        console.log('🛑 Stopping all audio to prevent duplicates...');
        
        // Stop ElevenLabs audio if playing
        if (this.currentAudio) {
            try {
                this.currentAudio.pause();
                this.currentAudio.currentTime = 0;
                this.currentAudio = null;
                console.log('✅ ElevenLabs audio stopped');
            } catch (error) {
                console.log('⚠️ Error stopping ElevenLabs audio:', error);
            }
        }
        
        // Stop browser TTS if playing
        if ('speechSynthesis' in window && speechSynthesis.speaking) {
            speechSynthesis.cancel();
            console.log('✅ Browser TTS stopped');
        }
        
        // Clear any queued audio
        this.audioQueue = [];
        this.isVoicePlaying = false;
        
        console.log('✅ All audio stopped successfully');
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
        console.log('🔍 Starting enhanced face detection with message caching...');
        
        setInterval(() => {
            if (!this.isProcessing && this.webcam.readyState === this.webcam.HAVE_ENOUGH_DATA) {
                this.detectFace();
            }
        }, 4000);
    }

    // 🚀 ENHANCED FACE DETECTION WITH MESSAGE CACHE SYSTEM
    async detectFace() {
        console.log('📸 Enhanced face detection with caching...');
        
        const imageData = this.captureFrame();
        
        if (imageData) {
            this.updateWebcamStatus('Face detected - Identifying...');
            this.updateAttendanceStatus('processing', '🔄 Identifying person...');
            this.isProcessing = true;
            
            try {
                const result = await this.recognizeFace(imageData);
                console.log('🎯 Recognition result:', result);
                await this.handleRecognitionResultWithCaching(result);
            } catch (error) {
                console.error('❌ Recognition error:', error);
                this.updateWebcamStatus('Recognition error - Please try again');
                this.updateAttendanceStatus('error', '❌ System error occurred');
                
                // 🔧 FIXED: Play error voice for recognition errors
                this.playYourElevenLabsHindi('सिस्टम में कुछ समस्या है। कृपया दोबारा कोशिश करें, धन्यवाद।');
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

    // 🚀 ENHANCED RECOGNITION RESULT HANDLING WITH MESSAGE CACHING
    async handleRecognitionResultWithCaching(result) {
        const now = Date.now();
        
        if (result.success && result.user_data) {
            console.log('✅ Person recognized:', result.user_data.name);
            
            this.currentUser = result.user_data;
            this.fillUserForm(result.user_data);
            
            const email = result.user_data.email;
            
            // 🚀 ENHANCED MESSAGE CACHING SYSTEM (like face_recognize_live.py)
            if (!this.messageCache[email] || now > this.messageCache[email].visibleUntil) {
                // First time or cache expired - full attendance process
                await this.markAttendanceWithCaching(result.user_data, result.session_info, now);
            } else {
                // 🚀 SMART VOICE REPETITION SYSTEM
                await this.handleCachedUserWithSmartVoice(email, result.user_data, now);
            }
            
        } else {
            console.log('❌ Recognition failed:', result.message);
            this.handleError(result);
        }
    }

    // 🚀 NEW: SMART VOICE REPETITION SYSTEM
    async handleCachedUserWithSmartVoice(email, userData, now) {
        const cached = this.messageCache[email];
        const timeSinceLastVoice = now - (cached.lastVoiceTime || 0);
        
        if (timeSinceLastVoice >= this.voiceSystem.repeatInterval) {
            const voiceMode = cached.voiceMode || this.voiceSystem.modes.SUCCESS;
            const voiceCount = cached.voiceCount || 1;
            
            let shouldPlayVoice = false;
            
            if (voiceMode === this.voiceSystem.modes.SUCCESS && voiceCount < this.voiceSystem.maxRepeats) {
                // ✅ SUCCESS: Play 3 times then stop
                shouldPlayVoice = true;
            } else if (voiceMode === this.voiceSystem.modes.ALREADY_MARKED && voiceCount < this.voiceSystem.maxRepeats) {
                // ✅ ALREADY MARKED: Play 3 times then stop
                shouldPlayVoice = true;
            } else if (voiceMode === this.voiceSystem.modes.WAIT_NEXT_DAY) {
                // ✅ WAIT NEXT DAY: Play infinitely
                shouldPlayVoice = true;
            }
            
            if (shouldPlayVoice) {
                // Get fresh voice message from backend
                const freshVoiceData = await this.getCurrentStateVoiceMessage(email, userData.name);
                
                if (freshVoiceData.success) {
                    this.playYourElevenLabsHindi(freshVoiceData.voice_message);
                    
                    // Update cache
                    this.messageCache[email].lastVoiceTime = now;
                    this.messageCache[email].voiceCount = voiceCount + 1;
                }
            }
        }
        
        // Display cached status message
        this.updateWebcamStatus(cached.webcamMessage || `Welcome back ${userData.name}!`);
        this.updateAttendanceStatus(cached.statusType || '', cached.statusMessage || 'Processing...');
    }

    // 🚀 NEW: GET CURRENT STATE VOICE MESSAGE FROM BACKEND
    async getCurrentStateVoiceMessage(email, name) {
        try {
            const response = await fetch(`/attendance/api/detailed_user_state/${email}/`);
            if (response.ok) {
                return await response.json();
            } else {
                return {
                    success: false,
                    voice_message: `हैप्पी थॉट्स ${name}, आपकी उपस्थिति दर्ज की गई है, धन्यवाद।`
                };
            }
        } catch (error) {
            console.error('Error getting voice message:', error);
            return {
                success: false,
                voice_message: `हैप्पी थॉट्स ${name}, आपकी उपस्थिति दर्ज की गई है, धन्यवाद।`
            };
        }
    }

    // 🔧 COMPLETELY FIXED: ATTENDANCE MARKING WITH PROPER ERROR HANDLING
    async markAttendanceWithCaching(userData, sessionInfo, now) {
        console.log('📋 Enhanced attendance marking for:', userData.name);
        
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
            console.log('📋 Enhanced attendance response:', result);
            console.log('📋 Response status:', response.status, response.statusText);
            
            // 🔧 CRITICAL FIX: Handle both success AND error responses properly
            if (response.ok && result.success) {
                // 🎉 SUCCESS - Enhanced handling
                console.log('✅ SUCCESS: Attendance marked successfully');
                await this.handleSuccessWithCaching(result, userData, now);
            } else {
                // 🔧 FIXED: Handle ALL error responses (409, 429, 403, etc.)
                console.log('❌ ERROR: Attendance marking failed');
                console.log('📋 Error details:', result);
                await this.handleErrorWithCaching(result, userData, now);
            }
            
        } catch (error) {
            console.error('❌ Network/System error during attendance marking:', error);
            
            // 🔧 FIXED: Better network error handling
            const networkErrorMessage = 'Network error - Please check connection';
            const hindiNetworkMessage = 'नेटवर्क की समस्या है। कृपया अपना इंटरनेट कनेक्शन जांचें, धन्यवाद।';
            
            this.updateWebcamStatus(networkErrorMessage);
            this.updateAttendanceStatus('error', '❌ Network error');
            
            // Cache network error
            this.messageCache[userData.email] = {
                visibleUntil: now + (this.MESSAGE_DISPLAY_SECONDS * 1000),
                lastVoiceTime: now,
                voiceCount: 1,
                voiceMode: this.voiceSystem.modes.WAIT_NEXT_DAY,
                webcamMessage: networkErrorMessage,
                statusType: 'error',
                statusMessage: '❌ Network error'
            };
            
            // 🔧 FIXED: Always play voice for network errors
            this.playYourElevenLabsHindi(hindiNetworkMessage);
        }
    }

    // 🚀 NEW: HANDLE SUCCESS WITH ENHANCED CACHING
    async handleSuccessWithCaching(result, userData, now) {
        // 🔧 FIXED: Extract Hindi voice message with fallback
        const hindiMessage = result.hindi_voice_message || 
                            result.voice_message || 
                            `हैप्पी थॉट्स ${userData.name}, आपकी उपस्थिति सफलतापूर्वक दर्ज हो गई है, धन्यवाद।`;
        
        const voiceMode = result.voice_mode || this.voiceSystem.modes.SUCCESS;
        
        // Display success message
        let statusMessage = '✅ Attendance Recorded Successfully!';
        
        // Enhanced status based on session progress
        if (result.day_number && result.total_days) {
            if (result.is_last_day) {
                statusMessage = `✅ Session Completed! (Day ${result.day_number}/${result.total_days})`;
            } else {
                statusMessage = `✅ Day ${result.day_number}/${result.total_days} Recorded!`;
            }
        } else if (result.attendance_type === 'repeat') {
            statusMessage = `✅ Repeat Attendance - Welcome Back!`;
        } else if (result.attendance_type === 'festival') {
            statusMessage = `✅ Festival Attendance Recorded!`;
        }
        
        this.updateWebcamStatus(`Welcome ${userData.name}! Attendance marked.`);
        this.updateAttendanceStatus('success', statusMessage);
        
        // 🚀 ENHANCED CACHING WITH VOICE MODE
        this.messageCache[userData.email] = {
            visibleUntil: now + (this.MESSAGE_DISPLAY_SECONDS * 1000),
            lastVoiceTime: now,
            voiceCount: 1,
            voiceMode: voiceMode,
            webcamMessage: `Welcome ${userData.name}! Attendance marked.`,
            statusType: 'success',
            statusMessage: statusMessage
        };
        
        // 🔥 CRITICAL FIX: ALWAYS play Hindi voice for success
        console.log('🔊 Playing success Hindi voice:', hindiMessage);
        this.playYourElevenLabsHindi(hindiMessage);
        
        // Reset after delay (like face_recognize_live.py)
        setTimeout(() => {
            this.resetAfterSuccess();
        }, 10000);
    }

    // 🔧 COMPLETELY FIXED: ERROR HANDLING WITH PROPER MESSAGE EXTRACTION
    async handleErrorWithCaching(result, userData, now) {
        console.log('🔧 Handling error with enhanced caching:', result);
        
        // 🔧 CRITICAL FIX: Extract Hindi voice message with multiple fallbacks
        const hindiMessage = result.hindi_voice_message || 
                            result.voice_message ||
                            this.getDefaultHindiErrorMessage(result, userData.name);
        
        const voiceMode = result.voice_mode || this.voiceSystem.modes.WAIT_NEXT_DAY;
        
        // 🔧 FIXED: Extract specific error message instead of generic "system error"
        let webcamMessage = result.error || result.message || 'Cannot mark attendance';
        let statusMessage = result.error || result.message || '❌ Cannot mark attendance';
        let statusType = 'error';
        
        // 🔧 ENHANCED: Handle specific error scenarios with proper categorization
        if (result.renewal_state === 'just_marked' || 
            (result.error && (result.error.includes('Already marked') || result.error.includes('just marked')))) {
            webcamMessage = `${userData.name} - Attendance already marked`;
            statusMessage = '⚠️ Attendance already marked!';
            statusType = 'duplicate';
            console.log('🔧 Detected: Already marked scenario');
            
        } else if (result.renewal_state === 'in_cooldown' || 
                   (result.error && result.error.includes('wait'))) {
            const hours = result.hours_remaining || 0;
            if (hours > 0) {
                webcamMessage = `Please wait ${hours.toFixed(1)} hours`;
                statusMessage = `⏳ Wait ${hours.toFixed(1)}h before next attendance`;
            } else {
                webcamMessage = `${userData.name} - Please wait before marking again`;
                statusMessage = '⏳ Please wait before next attendance';
            }
            statusType = 'duplicate';
            console.log('🔧 Detected: Cooldown scenario');
            
        } else if (result.error && result.error.includes('blacklisted')) {
            webcamMessage = 'Access denied - Blacklisted';
            statusMessage = '🚫 Access denied - Contact admin';
            statusType = 'error';
            
        } else if (result.error && result.error.includes('inactive')) {
            webcamMessage = 'Account inactive';
            statusMessage = '⚠️ Account inactive - Contact admin';
            statusType = 'error';
            
        } else if (result.error && result.error.includes('New User')) {
            webcamMessage = 'New user - Start with MA Shivir';
            statusMessage = '👋 New user - MA Shivir required';
            statusType = 'error';
            
        } else if (result.error && result.error.includes('Not Eligible')) {
            webcamMessage = 'Not eligible for current session';
            statusMessage = '❌ Not eligible - Complete previous sessions';
            statusType = 'error';
        }
        
        console.log('🔧 Final error messages:');
        console.log('   Webcam:', webcamMessage);
        console.log('   Status:', statusMessage);
        console.log('   Type:', statusType);
        console.log('   Hindi Voice:', hindiMessage);
        
        // 🔧 FIXED: Update UI with specific error messages (NOT "system error")
        this.updateWebcamStatus(webcamMessage);
        this.updateAttendanceStatus(statusType, statusMessage);
        
        // 🚀 ENHANCED ERROR CACHING WITH VOICE MODE
        this.messageCache[userData.email] = {
            visibleUntil: now + (this.MESSAGE_DISPLAY_SECONDS * 1000),
            lastVoiceTime: now,
            voiceCount: 1,
            voiceMode: voiceMode,
            webcamMessage: webcamMessage,
            statusType: statusType,
            statusMessage: statusMessage
        };
        
        // 🔥 CRITICAL FIX: ALWAYS play Hindi voice for errors
        console.log('🔊 Playing error Hindi voice:', hindiMessage);
        this.playYourElevenLabsHindi(hindiMessage);
    }

    // 🔧 NEW: Get default Hindi error messages based on error type
    getDefaultHindiErrorMessage(result, name) {
        if (result.renewal_state === 'just_marked' || 
            (result.error && (result.error.includes('Already marked') || result.error.includes('just marked')))) {
            return `हैप्पी थॉट्स ${name}, आपकी उपस्थिति पहले से ही दर्ज है, धन्यवाद।`;
        } else if (result.renewal_state === 'in_cooldown') {
            return `हैप्पी थॉट्स ${name}, कृपया थोड़ी देर बाद उपस्थिति दर्ज करें, धन्यवाद।`;
        } else if (result.error && result.error.includes('blacklisted')) {
            return `हैप्पी थॉट्स ${name}, आपका खाता प्रतिबंधित है। कृपया एडमिन से संपर्क करें, धन्यवाद।`;
        } else if (result.error && result.error.includes('inactive')) {
            return `हैप्पी थॉट्स ${name}, आपका खाता निष्क्रिय है। कृपया एडमिन से संपर्क करें, धन्यवाद।`;
        } else {
            return `हैप्पी थॉट्स ${name}, कुछ समस्या हुई है। कृपया दोबारा कोशिश करें, धन्यवाद।`;
        }
    }

    // 🔧 FIXED: CLEAN SHIVIR DISPLAY FUNCTION (FRONTEND FIX)
    cleanShivirDisplay(shivirData) {
        console.log('🧹 Cleaning shivir display:', shivirData);
        
        if (!shivirData || shivirData === '') {
            return 'New User';
        }
        
        // Handle string input - split by comma and clean each part
        const parts = shivirData.toString().split(',');
        const cleanedParts = [];
        const seen = new Set();
        
        for (let part of parts) {
            // 🔧 CRITICAL FIX: Remove '_COMPLETED' suffix correctly (without extra backslash)
            let cleanPart = part.trim().replace(/_COMPLETED/g, '').trim();
            
            // Only add if not empty and not already seen
            if (cleanPart && cleanPart !== '' && !seen.has(cleanPart)) {
                cleanedParts.push(cleanPart);
                seen.add(cleanPart);
            }
        }
        
        const result = cleanedParts.length > 0 ? cleanedParts.join(', ') : 'New User';
        console.log('✅ Cleaned shivir display:', result);
        return result;
    }

    // 🔧 FIXED: FILL USER FORM WITH CLEAN SHIVIR DISPLAY
    fillUserForm(userData) {
        console.log('📝 Filling form for user:', userData.name);
        
        this.clearForm();
        
        document.getElementById('userName').value = userData.name || '';
        document.getElementById('userEmail').value = userData.email || '';
        document.getElementById('userCity').value = userData.city || '';
        
        // 🔧 CRITICAL FIX: Clean shivir display before setting in form
        const rawShivir = userData.shivir_level || userData.shivir || '';
        const cleanShivir = this.cleanShivirDisplay(rawShivir);
        document.getElementById('userShivir').value = cleanShivir;
        
        document.getElementById('userStatus').value = userData.status || '';
        document.getElementById('sessionInfo').value = userData.current_session || '';
        
        console.log('✅ Form filled successfully for:', userData.name);
        console.log('🧹 Shivir display cleaned:', rawShivir, '→', cleanShivir);
    }

    // 🔧 ENHANCED: RECOGNITION ERROR HANDLER WITH BETTER VOICE INTEGRATION
    handleError(result) {
        console.log('🚨 Handling recognition error:', result.error_type);
        
        // Default Hindi messages for recognition errors
        let hindiMessage = 'माफ़ करें, कुछ समस्या हुई है। कृपया दोबारा कोशिश करें, धन्यवाद।';
        let voiceMode = this.voiceSystem.modes.WAIT_NEXT_DAY;
        
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
            case 'person_inactive_blacklisted':
            case 'person_blacklisted':
            case 'new_user_not_eligible':
            case 'not_eligible_for_session':
            case 'no_active_session':
                if (result.user_data) {
                    this.currentUser = result.user_data;
                    this.fillUserForm(result.user_data);
                    hindiMessage = result.hindi_voice_message || hindiMessage;
                    voiceMode = result.voice_mode || this.voiceSystem.modes.WAIT_NEXT_DAY;
                    
                    const now = Date.now();
                    this.messageCache[result.user_data.email] = {
                        visibleUntil: now + (this.MESSAGE_DISPLAY_SECONDS * 1000),
                        lastVoiceTime: now,
                        voiceCount: 1,
                        voiceMode: voiceMode,
                        webcamMessage: this.webcamStatus.textContent,
                        statusType: 'error',
                        statusMessage: this.attendanceStatus.querySelector('.status-message').textContent
                    };
                }
                
                this.updateWebcamStatus(result.message || 'Access denied');
                this.updateAttendanceStatus('error', '❌ ' + (result.message || 'Access denied'));
                break;
                
            case 'just_marked':
            case 'in_cooldown':
                if (result.user_data) {
                    this.currentUser = result.user_data;
                    this.fillUserForm(result.user_data);
                    hindiMessage = result.hindi_voice_message || hindiMessage;
                    voiceMode = result.voice_mode || this.voiceSystem.modes.ALREADY_MARKED;
                    
                    const now = Date.now();
                    this.messageCache[result.user_data.email] = {
                        visibleUntil: now + (this.MESSAGE_DISPLAY_SECONDS * 1000),
                        lastVoiceTime: now,
                        voiceCount: 1,
                        voiceMode: voiceMode,
                        webcamMessage: this.webcamStatus.textContent,
                        statusType: 'duplicate',
                        statusMessage: this.attendanceStatus.querySelector('.status-message').textContent
                    };
                }
                
                this.updateWebcamStatus(result.message || 'Please wait');
                this.updateAttendanceStatus('duplicate', '⏳ ' + (result.message || 'Please wait'));
                break;
                
            default:
                this.updateWebcamStatus('Recognition error occurred');
                this.updateAttendanceStatus('error', '❌ System error');
        }
        
        // 🔥 CRITICAL FIX: ALWAYS play Hindi voice for recognition errors
        console.log('🔊 Playing recognition error Hindi voice:', hindiMessage);
        this.playYourElevenLabsHindi(hindiMessage);
    }

    // 🚀 NEW: SESSION PROGRESS API INTEGRATION
    async getSessionProgress(email) {
        try {
            const response = await fetch(`/attendance/api/session_progress/${email}/`);
            if (response.ok) {
                return await response.json();
            } else {
                console.warn('Could not get session progress');
                return null;
            }
        } catch (error) {
            console.error('Error getting session progress:', error);
            return null;
        }
    }

    // 🚀 NEW: REPEAT ELIGIBILITY CHECK
    async checkRepeatEligibility(email) {
        try {
            const response = await fetch(`/attendance/api/check_repeat_eligibility/${email}/`);
            if (response.ok) {
                return await response.json();
            } else {
                console.warn('Could not check repeat eligibility');
                return null;
            }
        } catch (error) {
            console.error('Error checking repeat eligibility:', error);
            return null;
        }
    }

    // 🔥 YOUR MAIN ELEVENLABS HINDI VOICE FUNCTION (FIXED FOR DUPLICATES)
    async playYourElevenLabsHindi(hindiText) {
        if (!this.hindiVoiceEnabled || !hindiText) {
            console.log('⚠️ Hindi voice disabled or no text provided');
            return;
        }

        // 🔧 PREVENT OVERLAPPING CALLS
        if (this.isVoicePlaying) {
            console.log('⚠️ Voice already playing, skipping duplicate call...');
            return;
        }

        console.log('🔊 Playing YOUR ElevenLabs Hindi voice:', hindiText);

        // Method 1: Try YOUR ElevenLabs API for high-quality Hindi voice
        const elevenLabsSuccess = await this.callYourElevenLabsAPI(hindiText);
        
        // Method 2: Fallback to browser speech synthesis if YOUR API fails AND no voice is playing
        if (!elevenLabsSuccess && !this.isVoicePlaying) {
            setTimeout(() => {
                this.playBrowserHindiTTS(hindiText);
            }, 500);
        }
    }

    // 🔥 YOUR ELEVENLABS API INTEGRATION (FIXED FOR DUPLICATES)
    async callYourElevenLabsAPI(hindiText) {
        // ✅ STOP ANY EXISTING AUDIO FIRST
        this.stopAllAudio();
        
        if (this.isVoicePlaying) {
            console.log('⚠️ Voice already playing, skipping...');
            return false;
        }

        try {
            this.isVoicePlaying = true;
            console.log('🎵 Calling YOUR ElevenLabs API...');
            console.log('🔑 Using YOUR API Key:', this.elevenLabsApiKey.substring(0, 20) + '...');
            console.log('🎤 Using YOUR Voice ID:', this.hindiVoiceId);
            
            const response = await fetch(`https://api.elevenlabs.io/v1/text-to-speech/${this.hindiVoiceId}`, {
                method: 'POST',
                headers: {
                    'Accept': 'audio/mpeg',
                    'Content-Type': 'application/json',
                    'xi-api-key': this.elevenLabsApiKey
                },
                body: JSON.stringify({
                    text: hindiText,
                    model_id: "eleven_multilingual_v2",
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
                
                // ✅ CREATE SINGLE AUDIO INSTANCE
                this.currentAudio = new Audio(audioUrl);
                
                this.currentAudio.onended = () => {
                    URL.revokeObjectURL(audioUrl);
                    this.currentAudio = null;
                    this.isVoicePlaying = false;
                    console.log('✅ ElevenLabs audio finished');
                };
                
                this.currentAudio.onerror = () => {
                    this.currentAudio = null;
                    this.isVoicePlaying = false;
                    console.log('❌ ElevenLabs audio error');
                };
                
                this.currentAudio.onloadeddata = () => {
                    console.log('🎵 Audio loaded successfully');
                };
                
                await this.currentAudio.play();
                console.log('✅ YOUR ElevenLabs Hindi voice played successfully!');
                return true;
            } else {
                this.isVoicePlaying = false;
                const errorText = await response.text();
                console.log('⚠️ YOUR ElevenLabs API failed:', response.status, errorText);
                return false;
            }
        } catch (error) {
            this.isVoicePlaying = false;
            console.log('⚠️ YOUR ElevenLabs API error:', error.message);
            return false;
        }
    }

    // 🔥 BROWSER HINDI TTS (FIXED FOR DUPLICATES)
    playBrowserHindiTTS(hindiText) {
        // ✅ STOP ANY EXISTING AUDIO FIRST
        this.stopAllAudio();
        
        if (this.isVoicePlaying) {
            console.log('⚠️ Voice already playing, skipping browser TTS...');
            return;
        }

        console.log('🗣️ Using browser Hindi TTS fallback...');
        
        if ('speechSynthesis' in window) {
            this.isVoicePlaying = true;
            
            const utterance = new SpeechSynthesisUtterance(hindiText);
            utterance.lang = 'hi-IN';
            utterance.rate = 0.8;
            utterance.pitch = 1.0;
            utterance.volume = 0.8;
            
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
                this.isVoicePlaying = false;
                console.log('✅ Browser Hindi TTS completed');
            };
            
            utterance.onerror = () => {
                this.isVoicePlaying = false;
                console.log('❌ Browser TTS error');
            };
            
            speechSynthesis.speak(utterance);
        } else {
            this.isVoicePlaying = false;
            console.log('❌ Speech synthesis not supported');
        }
    }

    // 🚀 ENHANCED CLEANUP: Clear expired messages like face_recognize_live.py
    cleanupExpiredMessages() {
        const now = Date.now();
        const expiredEmails = Object.keys(this.messageCache).filter(email => 
            now > this.messageCache[email].visibleUntil
        );
        
        expiredEmails.forEach(email => {
            delete this.messageCache[email];
            console.log(`🧹 Cleaned up expired cache for ${email}`);
        });
    }

    // Start cleanup interval
    startMessageCleanup() {
        setInterval(() => {
            this.cleanupExpiredMessages();
        }, 5000); // Clean up every 5 seconds
    }

    // 🔥 UTILITY FUNCTIONS (ENHANCED)
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
        if (this.webcamStatus) {
            this.webcamStatus.textContent = message;
        }
        console.log('📺 Webcam status:', message);
    }

    updateAttendanceStatus(type, message) {
        if (this.attendanceStatus) {
            this.attendanceStatus.className = `attendance-status ${type}`;
            const statusMessageEl = this.attendanceStatus.querySelector('.status-message');
            if (statusMessageEl) {
                statusMessageEl.textContent = message;
            }
        }
        console.log('📊 Attendance status:', type, message);
    }

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

// Initialize the enhanced attendance system when page loads
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Initializing Enhanced Face Recognition Attendance System with FIXED error handling...');
    console.log('🔧 COMPLETELY FIXED: AI Voice & Error Display Issues Resolved + CLEAN SHIVIR DISPLAY!');
    const attendanceSystem = new AttendanceSystem();
    
    // Start message cleanup system
    attendanceSystem.startMessageCleanup();
    
    console.log('✅ Enhanced system ready with:');
    console.log('   🔧 FIXED Error Message Display');
    console.log('   🔊 FIXED AI Voice for All Scenarios');
    console.log('   🧹 FIXED Clean Shivir Display (No "_COMPLETED")');
    console.log('   🎵 Smart Voice Repetition System');
    console.log('   📊 Session Day Progress Tracking');
    console.log('   🗄️ Message Cache System');
    console.log('   🔄 Advanced User State Management');
    console.log('   🚀 All issues COMPLETELY RESOLVED!');
});
