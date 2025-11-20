from django.urls import path
from . import views

urlpatterns = [
    path("generate/<int:employee_id>/", views.generate_releaving, name="generate_releaving"),
]