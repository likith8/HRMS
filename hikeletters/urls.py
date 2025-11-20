# hikeletters/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('generate/<int:employee_id>/', views.generate_hike_letter, name='generate_hike_letter'),
]
