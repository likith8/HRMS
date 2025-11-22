from django.db import models
from employees.models import Employee

class OfferLetter(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    date_created = models.DateTimeField(auto_now_add=True)
    offer_date = models.DateField(null=True, blank=True)
    file = models.FileField(upload_to='offer_letters/')  # stores generated docx/pdf
    employee_code = models.CharField(max_length=20, blank=True, null=True)
    series_number = models.IntegerField(blank=True, null=True)
    variable_pay_per_annum = models.DecimalField(
        max_digits=14, 
        decimal_places=2, 
        default=0.00, 
        blank=True, 
        null=True,
        help_text="Optional Variable Pay (Annual) from offer letter"
    )

    def __str__(self):
        return f"Offer Letter for {self.employee.first_name}"