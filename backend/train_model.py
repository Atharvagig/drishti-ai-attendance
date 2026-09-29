import cv2
import os
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
LEGACY_DIR = os.path.join(BASE_DIR, 'legacy')

def train_recognizer(
    dataset_dir=os.path.join(DATA_DIR, 'dataset'),
    model_save_path=os.path.join(LEGACY_DIR, 'trainer.yml')
):
    """
    Reads the dataset folder, extracts faces and labels, and trains the LBPH model.
    """
    print("Initializing face recognizer...")
    # Initialize the LBPH face recognizer
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    
    # Initialize Haar Cascade for face detection
    face_cascade = cv2.CascadeClassifier(
        os.path.join(DATA_DIR, 'haarcascade_frontalface_default.xml'))
    
    faces = []
    labels = []
    
    # Dictionary to map names to integer IDs, and vice-versa if needed later
    label_dict = {}
    
    print("Reading images from dataset...")
    if not os.path.exists(dataset_dir):
        print(f"Error: Directory '{dataset_dir}' not found.")
        return
        
    for student_folder in os.listdir(dataset_dir):
        student_path = os.path.join(dataset_dir, student_folder)
        if not os.path.isdir(student_path):
            continue
            
        # Parse the folder name to get the ID. Our format is "Name_ID"
        try:
            name, student_id_str = student_folder.split('_')
            student_id = int(student_id_str)
        except ValueError:
            print(f"Skipping folder {student_folder}: Invalid naming format. Expected 'Name_ID'.")
            continue
            
        label_dict[student_id] = name
            
        # Process each image in the student's directory
        for img_name in os.listdir(student_path):
            if img_name.endswith(('.png', '.jpg', '.jpeg')):
                img_path = os.path.join(student_path, img_name)
                
                # Read image in grayscale
                img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
                
                # While images should already be cropped faces from the capture script,
                # we double-check to be robust.
                detected_faces = face_cascade.detectMultiScale(img, scaleFactor=1.1, minNeighbors=5)
                
                # If a face is found, append it to the training data
                for (x, y, w, h) in detected_faces:
                    faces.append(img[y:y+h, x:x+w])
                    labels.append(student_id)
                    
    if len(faces) == 0:
        print("No faces found to train on. Please run the capture script first.")
        return
        
    print(f"Training on {len(faces)} images for {len(label_dict)} student(s)...")
    recognizer.train(faces, np.array(labels))
    
    # Save the model
    recognizer.save(model_save_path)
    print(f"Training complete! Model saved to {model_save_path}")

if __name__ == "__main__":
    print("=== Training Face Recognition Model ===")
    train_recognizer()
