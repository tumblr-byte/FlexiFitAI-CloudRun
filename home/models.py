from django.db import models
from django.utils import timezone
import uuid


class Visitor(models.Model):
    HEALTH_CHOICES = [
        ('breast_cancer', 'Breast Cancer'),
        ('thyroid', 'Thyroid'),
        ('PCOS/PCOD', 'PCOS/PCOD'),
        ('general_health', 'General Health'),
    ]

    unique_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)



    name = models.CharField(max_length=100)
    profile_photo = models.ImageField(upload_to='profile_photos/', blank=True, null=True, default='img1.png')
    health_condition = models.CharField(max_length=50, choices=HEALTH_CHOICES)

    def __str__(self):
        return f"{self.name} ({self.unique_id})"


class HealthData(models.Model):
    ENERGY_CHOICES = [
        ("Low", "Low"),
        ("Medium", "Medium"),
        ("High", "High"),
    ]

    visitor = models.ForeignKey("Visitor", on_delete=models.CASCADE, related_name="health_entries")

    # "Had period?" yes/no choice (default False)
    had_period = models.BooleanField(default=False)

    # Allow empty values safely
    weight = models.FloatField(blank=True, null=True)
    energy = models.CharField(max_length=20, choices=ENERGY_CHOICES, blank=True, null=True, default=None)
    symptoms = models.CharField(max_length=255, blank=True, null=True, default=None)
    activities = models.TextField(blank=True, null=True, default=None)
    meals = models.TextField(blank=True, null=True, default=None)
    notes = models.TextField(blank=True, null=True, default=None)

    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def symptom_list(self):
        """Return symptoms as a clean list."""
        if not self.symptoms:
            return []
        return [s.strip() for s in self.symptoms.split(",") if s.strip()]

    def __str__(self):
        return f"Entry ({self.visitor.name}) on {self.created_at.date()}"