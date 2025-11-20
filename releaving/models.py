from django.db import models
from employees.models import Employee

class ReleavingLetter(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    releaving_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Releaving - {self.employee.first_name} {self.employee.last_name | ""}"
