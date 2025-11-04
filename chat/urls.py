# urls.py
from django.urls import path
from . import views

urlpatterns = [
     path('page/', views.chat_page, name='chat_page'),
  path("api/visitor_summary/", views.visitor_summary, name="visitor_summary"),
path("api/send_chat/", views.send_chat, name="send_chat"),
 path('page/<int:session_id>/', views.chat_page, name='chat_page'),


    path('api/history/', views.chat_history),
    path('api/history/<int:chat_id>/messages', views.chat_messages),
    path('api/history/<int:chat_id>/', views.delete_chat),
    path('api/history/delete_all/', views.delete_all_chats),
]
                                