from django import forms
from .models import Employee

class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = [
            "first_name", "last_name", "email",
            "phone", "address", "designation",
            "package_per_annum", "package_per_month", "is_draft"
        ]

    def clean(self):
        cleaned_data = super().clean()
        is_draft = cleaned_data.get("is_draft", True)
        first_name = cleaned_data.get("first_name")
        email = cleaned_data.get("email")

        # Always need first name + email
        if not first_name:
            self.add_error("first_name", "First Name is required")
        if not email:
            self.add_error("email", "Email is required")

        # For final submission, apply stricter validation (but NOT last_name)
        if not is_draft:
            required_fields = ["first_name", "email","phone","designation","address","package_per_annum", "package_per_month"]
            for field in required_fields:
                if not cleaned_data.get(field):
                    self.add_error(field, f"{field.replace('_',' ').title()} is required for final submission")

        return cleaned_data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["last_name"].required = False
