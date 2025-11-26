from django.db import models
from employees.models import Employee

class HikeLetter(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='hike_letters')
    date = models.DateField()  # Letter generation date
    hike_start_date = models.DateField()  # Next month's 1st automatically
    employee_code = models.CharField(max_length=20, blank=True, null=True)  # Fixed per employee
    old_package = models.DecimalField(max_digits=10, decimal_places=2)
    new_package = models.DecimalField(max_digits=10, decimal_places=2)
    hike_letter_file = models.FileField(upload_to="hike_letters/", blank=True, null=True)

    def __str__(self):
        return f"Hike Letter - {self.employee.first_name} ({self.employee_code})"
    
   
