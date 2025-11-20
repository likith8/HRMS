from django import forms
from .models import Payslip

class PayslipForm(forms.ModelForm):
    class Meta:
        model = Payslip
        fields = ['based_on', 'month_year', 'days_worked']
