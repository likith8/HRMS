from django.db import models
from employees.models import Employee

class OfferLetter(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    date_created = models.DateTimeField(auto_now_add=True)
    offer_date = models.DateField(null=True, blank=True)
    file = models.FileField(upload_to='offer_letters/')  # stores generated docx/pdf
    employee_code = models.CharField(max_length=20, blank=True, null=True)
    series_number = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return f"Offer Letter for {self.employee.first_name}"