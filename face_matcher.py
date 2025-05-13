import face_recognition
import numpy as np
import cv2
import os

def load_face_encodings_from_images(image_paths):
    encodings = {}
    for path in image_paths:
        image = face_recognition.load_image_file(path)
        faces = face_recognition.face_encodings(image)
        if faces:
            encodings[path] = faces[0]
    return encodings

def match_face(input_image_path, known_encodings):
    input_image = face_recognition.load_image_file(input_image_path)
    input_encoding = face_recognition.face_encodings(input_image)[0]
    
    matches = []
    for path, encoding in known_encodings.items():
        distance = np.linalg.norm(encoding - input_encoding)
        if distance < 0.6:  # You can tune this threshold
            matches.append((path, distance))
    matches.sort(key=lambda x: x[1])
    return matches
