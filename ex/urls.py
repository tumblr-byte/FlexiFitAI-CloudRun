from django.urls import path
from . import views

app_name = "ex"  


urlpatterns = [
    path('ai-coach/', views.ai_coach_view, name='ai_coach'),
 

    path('exercise/<str:name>/', views.exercise_detail, name='exercise_detail'),
  path('workout/<str:name>/', views.start_workout, name='start_workout'),

    # APIs
    path('api/classify/', views.classify_landmarks, name='classify_landmarks'),
    path('api/motivate/', views.motivate_user, name='motivate_user'),
    path('api/log/', views.log_workout, name='log_workout'),

]
     