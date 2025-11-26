# payslips/models.py

from django.db import models
from employees.models import Employee
from offerletters.models import OfferLetter
from hikeletters.models import HikeLetter


class Payslip(models.Model):
    BASED_ON_CHOICES = [
        ('offer', 'Offer Letter'),
        ('hike', 'Hike Letter'),
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    based_on = models.CharField(max_length=10, choices=BASED_ON_CHOICES)
    offer_letter = models.ForeignKey(OfferLetter, on_delete=models.SET_NULL, null=True, blank=True)
    hike_letter = models.ForeignKey(HikeLetter, on_delete=models.SET_NULL, null=True, blank=True)

    # Period instead of month
    month_year = models.CharField(max_length=20)  # Example: "November 2025"

    days_worked = models.PositiveIntegerField()
    gross_salary = models.DecimalField(max_digits=10, decimal_places=2)
    deductions = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    net_salary = models.DecimalField(max_digits=10, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)

    # THIS IS THE ONLY NEW FIELD — FOR DOWNLOAD BUTTON
    payslip_file = models.FileField(
        upload_to="payslips/",
        null=True,
        blank=True,
        help_text="Generated payslip document"
    )

    def __str__(self):
        return f"Payslip for {self.employee.get_full_name()} - {self.month_year}"

    class Meta:
        unique_together = ('employee', 'month_year')
        verbose_name = "Payslip"
        verbose_name_plural = "Payslips"