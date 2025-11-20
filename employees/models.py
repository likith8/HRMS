from django.db import models

# Create your models here.
class Employee(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField()
    phone = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    designation = models.CharField(max_length=100, blank=True, null=True)
    package_per_annum = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    package_per_month = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    is_draft = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    employee_code = models.CharField(max_length=20, blank=True, null=True)  # NEW FIELD

    def __str__(self):
        return f"{self.first_name} ({'Draft' if self.is_draft else 'Completed'})"