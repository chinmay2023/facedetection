# faceapp/hindi_messages.py
"""
Hindi Voice Messages for Tejgyan Foundation Face Recognition System
Extracted from face_recognize_live.py - Website stays English, Voice speaks Hindi
"""

def get_session_names():
    """Hindi names for all session types"""
    return {
        'MA': 'एम ए शिविर',
        'SSP1': 'एस एस पी वन शिविर', 
        'SSP2': 'एस एस पी टू शिविर',
        'HS1': 'हायर शिविर वन',
        'HS2': 'हायर शिविर टू',
        'FESTIVAL': 'त्योहार सत्संग'
    }

def get_attendance_marked_message(name, session_type):
    """General attendance marked message with session name"""
    session_names = get_session_names()
    session_hindi = session_names.get(session_type, 'शिविर')
    return f"हैप्पी थॉट्स {name}, {session_hindi} में आपकी उपस्थिति सफलतापूर्वक दर्ज हो गई है, धन्यवाद।"

def get_already_marked_message(name):
    """Already marked attendance message"""
    return f"हैप्पी थॉट्स {name}, आपकी उपस्थिति पहले ही दर्ज हो चुकी है। आपका समय और ध्यान देने के लिए धन्यवाद।"

def get_blacklist_message(name):
    """Blacklisted user message"""
    return f"हैप्पी थॉट्स {name}, आप वर्तमान में प्रतिबंधित सूची में हैं। कृपया एडमिन से संपर्क करें, धन्यवाद।"

def get_inactive_message(name):
    """Inactive user message"""
    return f"हैप्पी थॉट्स {name}, आप वर्तमान में निष्क्रिय हैं। कृपया एडमिन से संपर्क करके सक्रियता प्राप्त करें, धन्यवाद।"

def get_inactive_and_blacklisted_message(name):
    """Inactive and blacklisted message"""
    return f"हैप्पी थॉट्स {name}, आप वर्तमान में निष्क्रिय और प्रतिबंधित सूची दोनों में हैं। कृपया तुरंत एडमिन से संपर्क करें, धन्यवाद।"

def get_no_session_message(name):
    """No active session message"""
    return f"हैप्पी थॉट्स {name}, वर्तमान में कोई सक्रिय सत्र नहीं है। कृपया एडमिन से संपर्क करें, धन्यवाद।"

def get_system_error_message(name):
    """System error message"""
    return f"हैप्पी थॉट्स {name}, सिस्टम में कुछ समस्या है। कृपया दोबारा कोशिश करें, धन्यवाद।"

def get_person_not_found_message():
    """Person not found message"""
    return "माफ़ करें, आपकी पहचान नहीं हो सकी। कृपया पहले अपना पंजीकरण कराएं, धन्यवाद।"
