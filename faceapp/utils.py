# faceapp/utils.py
import face_recognition
import numpy as np

def encode_face_image(image_path):
    image = face_recognition.load_image_file(image_path)
    encodings = face_recognition.face_encodings(image)
    if encodings:
        return encodings[0]
    return None
