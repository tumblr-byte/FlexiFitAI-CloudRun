from django import forms
from .models import Visitor , HealthData

class VisitorForm(forms.ModelForm):
    class Meta:
        model = Visitor
        fields = ['name', 'profile_photo', 'health_condition']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Enter your name'}),
            'health_condition': forms.Select(),
        }




class HealthDataForm(forms.ModelForm):
    SYMPTOM_CHOICES = [
        ('Headache', 'Headache'),
        ('Cramps', 'Cramps'),
        ('Fatigue', 'Fatigue'),
        ('Mood Swings', 'Mood Swings'),
        ('Back Pain', 'Back Pain'),
    ]

    symptoms = forms.MultipleChoiceField(
        choices=SYMPTOM_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    class Meta:
        model = HealthData
        fields = ['had_period', 'weight', 'energy', 'symptoms', 'activities', 'meals', 'notes']
        widgets = {
            'had_period': forms.RadioSelect(choices=[(True, 'Yes'), (False, 'No')]),
            'weight': forms.NumberInput(attrs={'step': '0.1', 'placeholder': 'e.g., 55.2'}),
            'energy': forms.Select(attrs={'class': 'form-select'}),
            'activities': forms.Textarea(attrs={
                'rows': 2,
                'placeholder': 'e.g., 30 min walk, yoga session, light stretching',
            }),
            'meals': forms.Textarea(attrs={
                'rows': 2,
                'placeholder': 'e.g., Breakfast: oats, Lunch: pho, Dinner: salad',
            }),
            'notes': forms.Textarea(attrs={
                'rows': 2,
                'placeholder': 'Any extra notes — e.g., felt energetic after yoga',
            }),
        }