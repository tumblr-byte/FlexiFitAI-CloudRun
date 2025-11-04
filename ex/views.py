from django.shortcuts import render, redirect, get_object_or_404
from .forms import AICoachForm
from .models import AICoach , ExerciseSession , PoseLog
from google.cloud import aiplatform

import torch.nn as nn
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from google.oauth2 import service_account
from vertexai.generative_models import GenerativeModel
import numpy as np

import pandas as pd
import torch
import random
from home.models import Visitor
from .tech import PoseClassifier, setup_vertex_ai, ask_gemini

import json
from django.http import JsonResponse
from django.utils import timezone



def ai_coach_view(request):
    visitor_id = request.session.get('visitor_id')
    if not visitor_id:
        return redirect('visitor_registration')

    visitor = get_object_or_404(Visitor, id=visitor_id)

    # Generate exercise options
    class_names = ["Downdog", "Plank", "Warrior2", "Modified_Tree", "Standard_Tree"]
    random_choice = random.choice([x for x in class_names if x != "Standard_Tree"])
    exercises = ["Standard_Tree", random_choice]

    # Find or create coach for this visitor
    coach = getattr(visitor, 'ai_coach', None)

    # Handle form submission
    message = None
    if request.method == 'POST':
        form = AICoachForm(request.POST, instance=coach)
        if form.is_valid():
            coach = form.save(commit=False)
            coach.visitor = visitor  
            coach.save()
            message = "AI Coach saved successfully!"
            form = AICoachForm(instance=coach)
        else:
            message = "Please fix the errors below."
    else:
        form = AICoachForm(instance=coach)

    # Render the page
    return render(request, 'ex/index.html', {
        'form': form,
        'coach': coach,
        'message': message,
        'visitor': visitor,
        'exercises': exercises,
    })

     
# views.py
def exercise_detail(request, name):
    exercises_info = {
        "Downdog": {
            "title": "Downward Facing Dog",
            "intro": "A foundational yoga pose that stretches and strengthens the entire body while improving flexibility and circulation.",
            "how_to": [
                "Start on your hands and knees in tabletop position",
                "Spread your fingers wide and press firmly into the ground",
                "Tuck your toes and lift your hips up toward the ceiling",
                "Straighten your legs and press your heels toward the floor",
                "Keep your head between your arms and relax your neck",
                "Hold the position while breathing deeply"
            ],
            "benefits": [
                "Stretches shoulders, hamstrings, and calves",
                "Strengthens arms, legs, and core",
                "Improves blood circulation to the brain",
                "Relieves tension in the spine and back",
                "Energizes the entire body"
            ],
            "image": "images/Downdog.jpg",
            "rounds": 1,
            "duration": 20
        },
        "Plank": {
            "title": "Plank Pose",
            "intro": "A powerful core-strengthening exercise that builds endurance and stability throughout your entire body.",
            "how_to": [
                "Start in a push-up position with arms straight",
                "Place hands directly under your shoulders",
                "Keep your body in a straight line from head to heels",
                "Engage your core and squeeze your glutes",
                "Look down at the floor to keep neck neutral",
                "Hold the position without letting hips sag or rise"
            ],
            "benefits": [
                "Strengthens core muscles and abs",
                "Improves posture and spinal alignment",
                "Builds shoulder and arm strength",
                "Enhances overall body stability",
                "Increases endurance and stamina"
            ],
            "image": "images/Plank.jpg",
            "rounds": 1,
            "duration": 20
        },
        "Warrior2": {
            "title": "Warrior 2 Pose",
            "intro": "A powerful standing pose that builds strength, stability, and confidence while opening the hips and chest.",
            "how_to": [
                "Stand with feet wide apart (3-4 feet)",
                "Turn right foot out 90 degrees, left foot slightly in",
                "Bend your right knee over your right ankle",
                "Extend arms parallel to the floor",
                "Gaze over your right fingertips",
                "Keep your torso upright and centered",
                "Hold, then repeat on the other side"
            ],
            "benefits": [
                "Strengthens legs, ankles, and feet",
                "Opens hips and chest",
                "Improves focus and concentration",
                "Builds stamina and endurance",
                "Enhances balance and stability"
            ],
            "image": "images/Warrior2.jpg",
            "rounds": 1,
            "duration": 20
        },
        "Modified_Tree": {
            "title": "Modified Tree Pose",
            "intro": "A beginner-friendly version of the tree pose that helps you build balance and confidence.",
            "how_to": [
                "Stand straight with feet together",
                "Shift weight to your left foot",
                "Place right foot on your ankle or calf (avoid the knee)",
                "Keep toes touching the ground for extra support",
                "Bring hands together at chest",
                "Hold the position steadily",
                "Repeat on the other side"
            ],
            "benefits": [
                "Builds foundational balance skills",
                "Strengthens legs with less strain",
                "Improves confidence for advanced poses",
                "Suitable for beginners and seniors"
            ],
            "image": "images/Modified_Tree.jpg",
            "rounds": 2,
            "duration": 20
        },
        "Standard_Tree": {
            "title": "Standard Tree Pose",
            "intro": "A classic yoga pose that challenges your balance and focus while building strength throughout your body.",
            "how_to": [
                "Stand straight with feet together",
                "Shift weight to your left foot",
                "Place right foot on your inner left thigh",
                "Bring hands together at chest or raise overhead",
                "Hold the position and focus on a fixed point",
                "Repeat on the other side"
            ],
            "benefits": [
                "Improves balance and stability",
                "Strengthens legs, ankles, and core",
                "Enhances focus and concentration",
                "Improves posture and body alignment"
            ],
            "image": "images/Standard_Tree.jpg",
            "rounds": 1,
            "duration": 20
        },
    }

    exercise = exercises_info.get(name, {
        "title": name.replace('_', ' ').title(),
        "intro": "Description coming soon...",
        "how_to": [],
        "benefits": [],
        "image": f"images/{name}.jpg",
        "rounds": 2,
        "duration": 20
    })

    return render(request, 'ex/exercise_detail.html', {'name': name, 'exercise': exercise})


# --- load PyTorch model once ---
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
CLASS_NAMES = ["Downdog", "Plank", "Warrior2", "Modified_Tree", "Standard_Tree"]

def load_model(path="best.pth"):
    model = PoseClassifier(num_classes=len(CLASS_NAMES))
    model.load_state_dict(torch.load(path, map_location=device))
    model.to(device)
    model.eval()
    return model

MODEL = load_model("best.pth")

# --- setup Gemini (may return None if not configured) ---
try:
    GEMINI = setup_vertex_ai()
except Exception:
    GEMINI = None


# ---------------- page render ----------------
def start_workout(request, name):
    """
    URL: /workout/<name>/
    Use the visitor saved in session (visitor_id). If not found, redirect to register.
    """
    visitor = None
    ai_coach = None

    visitor_id = request.session.get("visitor_id")
    if not visitor_id:
        # no visitor in session — either redirect to registration or choose a safe fallback
        return redirect('visitor_registration')

    # fetch visitor and their coach — guarantees the right pair
    visitor = get_object_or_404(Visitor, id=visitor_id)
    ai_coach = getattr(visitor, 'ai_coach', None)  # returns None if not set

    # You may want to create a default coach for visitor if none exists:
    # if not ai_coach:
    #     ai_coach = AICoach.objects.create(visitor=visitor, name="Gemini", personality="friendly")

    # pass personality_display explicitly (safer for templates/JS)
    personality_display = ai_coach.get_personality_display() if ai_coach else "Friendly"

    return render(request, "ex/workout.html", {
        "target_pose": name,
        "visitor": visitor,
        "ai_coach": ai_coach,
        "ai_name": ai_coach.name if ai_coach else "Gemini",
        "ai_personality_display": personality_display,
    })

# ---------------- classify landmarks ----------------
@csrf_exempt
def classify_landmarks(request):
    import mediapipe as mp
    """
    POST JSON: { "landmarks": [[x,y,z], ...] }
    Returns: { "predicted": str, "confidence": float }
    """
    if request.method != "POST":
        return HttpResponseBadRequest("Use POST")

    try:
        data = json.loads(request.body)
        lm = data.get("landmarks")
        if not lm:
            return JsonResponse({"predicted": "None", "confidence": 0.0})

        # flatten
        flat = [coord for point in lm for coord in point]
        input_tensor = torch.tensor(flat, dtype=torch.float32).unsqueeze(0).to(device)
        with torch.no_grad():
            output = MODEL(input_tensor)
            probs = torch.softmax(output, dim=1).cpu().numpy()[0]
            pred_idx = int(np.argmax(probs))
            confidence = float(probs[pred_idx])
            predicted = CLASS_NAMES[pred_idx]

        # Only accept if >= 0.75 as you wanted
        if confidence < 0.75:
            return JsonResponse({"predicted": "None", "confidence": confidence})
        return JsonResponse({"predicted": predicted, "confidence": confidence})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# ---------------- gemini motivation endpoint ----------------
@csrf_exempt
def motivate_user(request):
    import mediapipe as mp
    """
    POST JSON: { "ai_name": str, "personality": str, "pose": str, "status": "halfway"|"complete"|"help" }
    Returns: { "text": "<gemini reply or fallback>" }
    """
    if request.method != "POST":
        return HttpResponseBadRequest("Use POST")
    try:
        data = json.loads(request.body)
        ai_name = data.get("ai_name", "Coach")
        personality = data.get("personality", "")
        pose = data.get("pose", "")
        status = data.get("status", "halfway")

        # Build a small prompt tailored to status and personality
        if status == "halfway":
            prompt = f"{ai_name} ({personality}) — give one short encouraging sentence to a user holding the {pose} pose at the halfway mark. Keep it friendly and motivating."
        elif status == "complete":
            prompt = f"{ai_name} ({personality}) — give a short congratulatory line for completing the {pose} pose. Keep it positive and concise."
        elif status == "help":
            prompt = f"{ai_name} ({personality}) — user asked for help during {pose}. Provide a short supportive reply and suggest switching to Modified_Tree if appropriate."
        else:
            prompt = f"{ai_name} ({personality}) — short motivational line."

        # Try using ask_gemini; if GEMINI is not configured, fallback to simple canned replies
        reply = None
        try: 
            if GEMINI:
                # adapt ask_gemini signature as in your main.py; here we try to pass personality if supported
                # ask_gemini(prompt, personality=personality) or ask_gemini(prompt)
                try:
                    reply = ask_gemini(prompt, personality=personality)
                except TypeError:
                    reply = ask_gemini(prompt)
            else:
                reply = None
        except Exception:
            reply = None

        if not reply:
            # fallback simple canned message per status
            if status == "halfway":
                reply = "You're doing great — keep it steady for the next 10 seconds!"
            elif status == "complete":
                reply = "Beautiful work — you nailed that rep!"
            elif status == "help":
                reply = "No worries — let's switch to a modified version and take it slow."
            else:
                reply = "Keep going, you're doing well!"

        return JsonResponse({"text": str(reply)})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# ---------------- logging endpoint (visitor-safe) ----------------
@csrf_exempt
def log_workout(request):
    import mediapipe as mp
    """
    POST JSON:
    {
      "visitor_id": optional (auto-detected from session if missing),
      "coach_id": optional,
      "target_pose": str,
      "detected_pose": str,
      "time_duration": float,
      "confidence": float,
      "event": "round_complete"|"misaligned"|"help_switched"|...
    }
    """
    if request.method != "POST":
        return HttpResponseBadRequest("Use POST")

    try:
        # Load JSON data
        data = json.loads(request.body or "{}")

        # Secure visitor resolution: session first, then fallback to JSON
        visitor_id = request.session.get("visitor_id") or data.get("visitor_id")
        if not visitor_id:
            return JsonResponse({"error": "No visitor in session or payload."}, status=401)

        # Fetch correct visitor
        try:
            visitor_obj = Visitor.objects.get(pk=int(visitor_id))
        except Visitor.DoesNotExist:
            return JsonResponse({"error": "Visitor not found."}, status=404)

        coach_id = data.get("coach_id")
        target_pose = data.get("target_pose", "")
        detected_pose = data.get("detected_pose", "")
        time_duration = float(data.get("time_duration", 0.0))
        confidence = float(data.get("confidence", 0.0))
        event = data.get("event", "")

        # Always link logs to *this visitor’s* current unfinished session for that pose
        session, _ = ExerciseSession.objects.get_or_create(
            visitor=visitor_obj,
            coach_id=coach_id,
            target_pose=target_pose,
            finished_at__isnull=True
        )

        # Handle misalignment counter safely per-visitor session
        if event == "misaligned":
            session.misaligned_count += 1
            session.save()

        # Create new PoseLog for this visitor only
        log = PoseLog.objects.create(
            session=session,
            timestamp=timezone.now(),
            target_pose=target_pose,
            detected_pose=detected_pose,
            time_duration=time_duration,
            confidence=confidence,
            misaligned_count=session.misaligned_count,
        )

        # Close session if finished
        if event == "session_finished":
            session.finished_at = timezone.now()
            session.save()

        return JsonResponse({
            "status": "ok",
            "visitor": visitor_obj.name,
            "session_id": session.id,
            "log_id": log.id,
            "misaligned_count": session.misaligned_count,
        })

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
