from django.contrib import admin
from django.urls import path 
from . import views


urlpatterns = [
    path('' , views.home , name = "home"),
     path('register/', views.visitor_registration, name='visitor_registration'),
   path("journal/", views.health_journal_view, name="journal"),
 
    path("journal/delete/<int:pk>/", views.delete_entry, name="delete"),
    path('health/<int:visitor_id>/', views.health_tracker, name='health_tracker'),
   ]                 