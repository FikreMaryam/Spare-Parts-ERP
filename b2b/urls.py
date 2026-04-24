from django.urls import path
from . import views

app_name = 'b2b'

urlpatterns = [
    path('', views.network_home, name='network_home'),
    path('request/', views.request_connection, name='request_connection'),
    path('accept/<int:connection_id>/', views.accept_connection, name='accept_connection'),
    path('chat/<int:connection_id>/', views.b2b_chat, name='b2b_chat'),
]
