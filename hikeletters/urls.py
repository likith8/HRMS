# hikeletters/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('generate/<int:employee_id>/', views.generate_hike_letter, name='generate_hike_letter'),
    # path('download/<int:pk>/',views.download_hike_letter,name='download_hike_letter'),
]
