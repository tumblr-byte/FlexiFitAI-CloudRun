# views.py
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import ChatSession, ChatMessage
from .serializers import ChatMessageSerializer, ChatSessionSerializer
from .gemini import get_gemini_reply
from django.shortcuts import get_object_or_404
from home.models import Visitor , HealthData
from ex.models import AICoach , PoseLog
from django.shortcuts import render , redirect
from .forms import ChatForm
  

@api_view(['GET'])
def visitor_summary(request):
    visitor_id = request.session.get('visitor_id')
    if not visitor_id:
        return Response({"error": "No visitor in session"}, status=401)

    visitor = get_object_or_404(Visitor, id=visitor_id)
    ai = getattr(visitor, 'ai_coach', None)
    latest_health = visitor.health_entries.order_by('-created_at').first()

    summary = {
        "name": visitor.name,
        "profile_photo_url": visitor.profile_photo.url if visitor.profile_photo else "/static/img1.jpg",
        "condition": visitor.health_condition,
        "ai_name": ai.name if ai else "Gemini",
        "personality_key": ai.personality if ai else "friendly",
        "personality_display": ai.get_personality_display() if ai else "Friendly",
        "latest_health_summary": f"Energy: {latest_health.energy}, Symptoms: {latest_health.symptoms}" if latest_health else "No data yet.",
    }
    return Response(summary)



@api_view(['GET'])
def chat_history(request):
    visitor_id = request.session.get('visitor_id')
    if not visitor_id:
        return Response({"error": "No visitor in session"}, status=401)

    sessions = ChatSession.objects.filter(visitor_id=visitor_id).order_by('-created_at')
    return Response(ChatSessionSerializer(sessions, many=True).data)



@api_view(['GET'])
def chat_messages(request, chat_id):
    visitor_id = request.session.get('visitor_id')
    if not visitor_id:
        return Response({"error": "No visitor in session"}, status=401)

    session = get_object_or_404(ChatSession, id=chat_id, visitor_id=visitor_id)
    data = {
        "session_id": session.id,
        "ai_name": session.coach.name if session.coach else "Gemini",
        "personality": session.coach.personality if session.coach else "friendly",
        "messages": ChatMessageSerializer(session.messages.order_by('created_at'), many=True).data,
    }
    return Response(data)


@api_view(['POST'])
def send_chat(request):
    visitor_id = request.session.get('visitor_id')
    if not visitor_id:
        return Response({"error": "No visitor in session"}, status=401)

    message = request.data.get('message')
    session_id = request.data.get('session_id')

    visitor = get_object_or_404(Visitor, id=visitor_id)
    coach = getattr(visitor, 'ai_coach', None)

    
    if session_id:
        session, _ = ChatSession.objects.get_or_create(id=session_id, visitor=visitor, coach=coach)
    else:
        session = ChatSession.objects.create(visitor=visitor, coach=coach)

    ChatMessage.objects.create(session=session, role='user', text=message)


    latest_health = visitor.health_entries.order_by('-created_at').first()
    health_summary = (
        f"- Had Period: {'Yes' if latest_health.had_period else 'No'}\n"
        f"- Weight: {latest_health.weight or 'Not logged'} kg\n"
        f"- Energy: {latest_health.energy or 'Unknown'}\n"
        f"- Symptoms: {latest_health.symptoms or 'None'}\n"
        f"- Activities: {latest_health.activities or 'None'}\n"
        f"- Meals: {latest_health.meals or 'None'}\n"
        f"- Notes: {latest_health.notes or 'None'}\n"
        if latest_health else
        "No health records found yet."
    )


    latest_pose = PoseLog.objects.filter(session__visitor=visitor).order_by('-timestamp').first()
    exercise_summary = (
        f"- Pose: {latest_pose.detected_pose}\n"
        f"- Duration: {latest_pose.time_duration:.1f} sec\n"
        f"- Confidence: {latest_pose.confidence:.2f}"
        if latest_pose else
        "No exercise recorded recently."
    )


    context = f"""
You are an AI wellness and fitness coach named **{coach.name if coach else 'Gemini'}**.
Your personality is **{coach.get_personality_display() if coach else 'Friendly'}** — keep that tone consistent.

You are helping **{visitor.name}**, who has **{visitor.health_condition}**.

Recent Health Data:
{health_summary}

Recent Exercise Data:
{exercise_summary}

Rules for response:
1. Always analyze user’s message in relation to their health data.
2. If the user asks about **exercise**, suggest at least 3 specific poses or routines by name.
   - Include names like Tree Pose, Bridge Pose, Cat-Cow Stretch, etc.
   - Mention how each helps their condition.
3. If the user asks about **budget or diet**, create a clear meal plan within their mentioned budget.
   - Give breakfast, lunch, dinner ideas with local/affordable foods.
4. If the user hasn’t done exercises or logged meals, mention it kindly.
   - Example: “I noticed you haven’t logged a workout recently — want me to plan a gentle 10-minute yoga routine?”
5. Keep tone personal, warm, and short — as if you really know them.
6. Use emojis if natural, e.g., 🌸💪🍎

Now, the user says:
"{message}"

Reply as {coach.name if coach else 'Gemini'}:
"""

    reply = get_gemini_reply(context, coach.personality if coach else 'friendly')

    ChatMessage.objects.create(session=session, role='coach', text=reply)

    return Response({
        "session_id": session.id,
        "reply": reply,
        "ai_name": coach.name if coach else "Gemini",
        "personality_key": coach.personality if coach else "friendly",
    })



@api_view(['DELETE'])
def delete_chat(request, chat_id):
    visitor_id = request.session.get('visitor_id')
    if not visitor_id:
        return Response({"error": "No visitor in session"}, status=401)

    ChatSession.objects.filter(id=chat_id, visitor_id=visitor_id).delete()
    return Response(status=status.HTTP_204_NO_CONTENT)



@api_view(['POST'])
def delete_all_chats(request):
    visitor_id = request.session.get('visitor_id')
    if not visitor_id:
        return Response({"error": "No visitor in session"}, status=401)

    ChatSession.objects.filter(visitor_id=visitor_id).delete()
    return Response({"message": "All chats deleted."})


def chat_page(request, session_id=None):
    visitor_id = request.session.get('visitor_id')
    if not visitor_id:
        return redirect('visitor_registration')

    visitor = get_object_or_404(Visitor, id=visitor_id)
    coach = getattr(visitor, 'ai_coach', None)

    # Get or create the selected chat session
    if session_id:
        session = get_object_or_404(ChatSession, id=session_id, visitor=visitor)
    else:
        session, _ = ChatSession.objects.get_or_create(visitor=visitor, coach=coach)

    # Handle delete single chat
    if request.method == "POST" and "delete_chat" in request.POST:
        session.delete()
        return redirect('chat_page')

    # Handle delete all chats
    if request.method == "POST" and "delete_all" in request.POST:
        ChatSession.objects.filter(visitor=visitor).delete()
        return redirect('chat_page')

    # Handle sending message
    if request.method == "POST" and "send_message" in request.POST:
        form = ChatForm(request.POST)
        if form.is_valid():
            message = form.cleaned_data['message']
            ChatMessage.objects.create(session=session, role='user', text=message)

            # Build context for AI
            latest_health = visitor.health_entries.order_by('-created_at').first()
            latest_pose = PoseLog.objects.filter(session__visitor=visitor).order_by('-timestamp').first()

            health_summary = f"Energy: {latest_health.energy}, Symptoms: {latest_health.symptoms}" if latest_health else "No health data yet."
            exercise_summary = f"Last exercise: {latest_pose.detected_pose}" if latest_pose else "No exercise data yet."

            context = f"""
            You are {coach.name if coach else 'Gemini'}, {coach.get_personality_display() if coach else 'Friendly'} personality.
            You are talking with {visitor.name}, who has {visitor.health_condition}.
            Health: {health_summary}
            Exercise: {exercise_summary}
            User: {message}
            """

            reply = get_gemini_reply(context, coach.personality if coach else 'friendly')
            ChatMessage.objects.create(session=session, role='coach', text=reply)
            return redirect('chat_page', session_id=session.id)
    else:
        form = ChatForm()

    sessions = ChatSession.objects.filter(visitor=visitor).order_by('-created_at')
    messages = session.messages.order_by('created_at')

    return render(request, 'chat/chat.html', {
        'form': form,
        'messages': messages,
        'sessions': sessions,
        'session': session,
        'ai_name': coach.name if coach else 'Gemini',
        'ai_personality': coach.get_personality_display() if coach else 'Friendly',
        'visitor': visitor,
    })
