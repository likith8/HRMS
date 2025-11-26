from django.db import models
from employees.models import Employee

class ReleavingLetter(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE,related_name='releaving_letters')
    releaving_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    placed_in_company = models.CharField(
        max_length=200,
        blank=True,
        null=True
    )
    letter_file = models.FileField(
        upload_to='releaving_letters/',
        blank=True,
        null=True
    )

    def __str__(self):
        return f"Releaving - {self.employee.first_name} - {self.employee.employee_code or ''}"
