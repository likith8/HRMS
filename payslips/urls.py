from django.urls import path
from . import views

urlpatterns = [
    path('generate/<int:employee_id>/', views.generate_payslip, name='generate_payslip'),
]
