from django.urls import path
from . import views
app_name="employees"
urlpatterns = [
    path('add/', views.add_employee, name='add_employee'),
    path('list/', views.employee_list, name='employee_list'),
    path('edit/<int:id>/', views.edit_employee, name='edit_employee'),
    path('delete/<int:id>/', views.delete_employee, name='delete_employee'),
    path('check_unique/', views.check_unique_employee, name='check_unique_employee'),
    path('master-report/', views.employee_master_report, name='employee_master_report'),
]