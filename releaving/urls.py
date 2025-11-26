from django.urls import path
from . import views

urlpatterns = [
    path("generate/<int:employee_id>/", views.generate_releaving, name="generate_releaving"),
    path("releaving/<int:employee_id>/download/", views.download_releaving_letter, name="download_releaving_letter"),
]