from django.db import models
from django.utils import timezone

class ChatSession(models.Model):
    visitor = models.ForeignKey('home.Visitor', on_delete=models.CASCADE, related_name='chat_sessions')
    coach = models.ForeignKey('ex.AICoach', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Chat with {self.coach.name if self.coach else 'Gemini'} @ {self.created_at}"

        
class ChatMessage(models.Model):
    ROLE_CHOICES = [('user', 'User'), ('coach', 'Coach')]
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    text = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.role}: {self.text[:30]}"
    