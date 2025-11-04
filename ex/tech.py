from google.cloud import aiplatform
from google.oauth2 import service_account
from vertexai.generative_models import GenerativeModel
import torch.nn as nn
import torch
import numpy as np
import mediapipe as mp
import pandas as pd
import cv2
import os
from mediapipe.framework.formats import landmark_pb2
                                               
angles_df = pd.read_csv("2.csv")

mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose

 
def setup_vertex_ai():
    # Read environment variables
    project_id = os.environ.get("GEMINI_PROJECT_ID")
    location = os.environ.get("GEMINI_LOCATION", "us-central1")
    credentials_path = os.environ.get("GEMINI_CREDENTIALS_PATH")

    # Load credentials from the file path (either local .env or mounted secret in Cloud Run)
    credentials = service_account.Credentials.from_service_account_file(credentials_path)

    # Initialize Vertex AI / Gemini
    aiplatform.init(   
        project=project_id,
        location=location,
        credentials=credentials
    )

    # Return a Gemini model instance
    return GenerativeModel("gemini-2.5-flash")



class PoseClassifier(nn.Module):
    def __init__(self, num_classes):
        super().__init__()
        self.model = nn.Sequential(
            nn.Linear(99, 128),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, num_classes)
        )

    def forward(self, x):
        return self.model(x)
    

def calculate_angle(a, b, c):
    a, b, c = np.array(a), np.array(b), np.array(c)
    ba, bc = a - b, c - b
    cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-6)
    cosine_angle = np.clip(cosine_angle, -1, 1)
    return np.degrees(np.arccos(cosine_angle))

def draw_pose(frame, lm, target_pose, detected_pose):
    if lm is None:
        return frame

    # Color green if correct pose, red otherwise
    color = (0, 255, 0) if detected_pose == target_pose else (0, 0, 255)

    landmark_spec = mp_drawing.DrawingSpec(color=color, thickness=3, circle_radius=4)
    connection_spec = mp_drawing.DrawingSpec(color=color, thickness=2)

    mp_lm = landmark_pb2.LandmarkList()
    for x, y, z in lm:
        mp_lm.landmark.add(x=float(x), y=float(y), z=float(z))

    mp_drawing.draw_landmarks(
        frame,
        mp_lm,
        mp_pose.POSE_CONNECTIONS,     # this draws the skeleton
        landmark_drawing_spec=landmark_spec,
        connection_drawing_spec=connection_spec
    )
    return frame


def draw_angle(frame, lm, target_pose):
    h, w, _ = frame.shape
    pose_data = angles_df[angles_df['class'] == target_pose]

    for _, row in pose_data.iterrows():
        a = int(row['a'])
        b = int(row['b'])
        c = int(row['c'])
        name = row['name']

        # get landmarks
        pa = lm[a]
        pb = lm[b]
        pc = lm[c]

        # calculate angle
        ang = calculate_angle(pa, pb, pc)

        # draw text on frame
        cx, cy = int(pb.x * w), int(pb.y * h)
        cv2.putText(frame, f"{name}: {int(ang)}°", (cx + 10, cy - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

    return frame  # make sure return is OUTSIDE the loop



# Setup Gemini model
gemini_model = setup_vertex_ai()

def ask_gemini(target_text, model=gemini_model, temperature=0.6, max_output_tokens=80):

        response = model.generate_content(
            target_text,
            generation_config={
                "temperature": temperature,
                "max_output_tokens": max_output_tokens,
                "top_p": 0.9,
                "top_k": 40
            }
        )
        return response.text.strip()