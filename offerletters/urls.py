# offerletters/urls.py
from django.urls import path
from . import views



urlpatterns = [
    path('generate/<int:employee_id>/', views.generate_offer_letter, name='generate_offer_letter'),
]