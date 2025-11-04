# serializers.py
from rest_framework import serializers
from .models import ChatSession, ChatMessage 
from home.models import Visitor , HealthData
from ex.models import AICoach

class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ['role', 'text', 'created_at']

class ChatSessionSerializer(serializers.ModelSerializer):
    snippet = serializers.SerializerMethodField()

    class Meta:
        model = ChatSession
        fields = ['id', 'created_at', 'snippet']

    def get_snippet(self, obj):
        msg = obj.messages.last()
        return msg.text[:80] + "..." if msg else ""
         