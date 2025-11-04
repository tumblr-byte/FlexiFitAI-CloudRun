
from django.conf import settings
from django.db import models
from django.utils import timezone
from home.models import Visitor  

class AICoach(models.Model):
    PERSONALITY_CHOICES = [        
        ('genz', 'Gen-Z'), 
        ('calm', 'Calm'),
        ('friendly', 'Friendly'),
    ]   

    visitor = models.OneToOneField(Visitor, on_delete=models.CASCADE, related_name='ai_coach')
    name = models.CharField(max_length=100)
    personality = models.CharField(max_length=20, choices=PERSONALITY_CHOICES)

    def __str__(self):
        return f"{self.name} ({self.get_personality_display()}) for {self.visitor.name}"

class ExerciseSession(models.Model):
    visitor = models.ForeignKey(Visitor, on_delete=models.CASCADE, null=True, blank=True)
    coach = models.ForeignKey(AICoach, on_delete=models.SET_NULL, null=True, blank=True)
    target_pose = models.CharField(max_length=100)
    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True, blank=True)
    misaligned_count = models.PositiveIntegerField(default=0)  

    def __str__(self):
        return f"{self.visitor} - {self.target_pose} @ {self.started_at}"



class PoseLog(models.Model):
    session = models.ForeignKey(
        ExerciseSession, on_delete=models.CASCADE, related_name='pose_logs', null=True, blank=True
    )
    timestamp = models.DateTimeField(default=timezone.now)
    target_pose = models.CharField(max_length=100)
    detected_pose = models.CharField(max_length=100)
    time_duration = models.FloatField(help_text="Duration in seconds", default=0.0)
    confidence = models.FloatField(default=0.0)
    misaligned_count = models.PositiveIntegerField(default=0)  

    def __str__(self):
        return f"{self.timestamp}: {self.detected_pose} ({self.confidence:.2f})"
