from django import forms
from .models import AICoach

class AICoachForm(forms.ModelForm):
    class Meta:
        model = AICoach
        fields = ['name', 'personality']
        widgets = {
            'name': forms.TextInput(attrs={
                'placeholder': 'What do you want to name your AI Coach?',
                'class': 'form-control'
            }),
            'personality': forms.Select(attrs={'class': 'form-control'}),
        }
              