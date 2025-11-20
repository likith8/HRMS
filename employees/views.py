from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import Employee
from .forms import EmployeeForm
from django.http import JsonResponse

# -------------------------------
# ADD EMPLOYEE
# -------------------------------
def add_employee(request):
    if request.method == "POST":
        action = request.POST.get("action")
        form = EmployeeForm(request.POST)

        # --- Save as Draft ---
        if action == "draft":
            first_name = request.POST.get("first_name", "").strip()
            email = request.POST.get("email", "").strip()

            if not first_name or not email:
                messages.error(request, "First Name and Email are required to save a draft.")
                return render(request, "employees/add_employee.html", {"form": form})

            # manually create draft (bypass strict validation)
            employee = Employee(
                first_name=first_name,
                last_name=request.POST.get("last_name", "").strip() or "",
                email=email,
                phone=request.POST.get("phone", "").strip() or None,
                address=request.POST.get("address", "").strip() or None,
                designation=request.POST.get("designation", "").strip() or None,
                package_per_annum=request.POST.get("package_per_annum") or None,
                package_per_month=request.POST.get("package_per_month") or None,
                is_draft=True,
            )
            employee.save()
            messages.info(request, "Draft saved successfully.")
            return redirect("employee_list")

        # --- Final Submission ---
        elif action == "final":
            if form.is_valid():
                email = form.cleaned_data.get('email')
                phone = form.cleaned_data.get('phone')

                # --- Uniqueness Checks ---
                email_exists = Employee.objects.filter(email__iexact=email, is_draft=False).exists()
                phone_exists = Employee.objects.filter(phone__iexact=phone, is_draft=False).exists()

                if email_exists and phone_exists:
                    messages.error(request, "Both email and phone number already exist.")
                elif email_exists:
                    messages.error(request, "Email already exists.")
                elif phone_exists:
                    messages.error(request, "Phone number already exists.")
                else:
                    employee = form.save(commit=False)
                    employee.is_draft = False
                    employee.save()
                    messages.success(request, "Employee details saved successfully.")
                    return redirect("employee_list")
            else:
                messages.error(request, "Please correct the highlighted errors before final submission.")

    else:
        form = EmployeeForm()

    return render(request, "employees/add_employee.html", {"form": form})


# -------------------------------
# LIST EMPLOYEES
# -------------------------------
def employee_list(request):
    employees = Employee.objects.all().order_by("-created_at")

    if request.method == "POST":
        search_value = request.POST.get("search", "").strip()

        if search_value:
            # Filter by employee_code first
            by_code = employees.filter(employee_code__icontains=search_value)
            # Filter by phone
            by_phone = employees.filter(phone__icontains=search_value)
            # Combine the two querysets using `|` (union)
            employees = by_code | by_phone

    return render(request, "employees/employee_list.html", {"employees": employees})


# -------------------------------
# EDIT EMPLOYEE
# -------------------------------
def edit_employee(request, id):
    employee = get_object_or_404(Employee, id=id)

    if request.method == "POST":
        form = EmployeeForm(request.POST, instance=employee)
        action = request.POST.get("action")

        # --- Save Draft ---
        if action == "draft":
            first_name = request.POST.get("first_name", "").strip()
            email = request.POST.get("email", "").strip()

            if not first_name or not email:
                messages.error(request, "First Name and Email are required to save a draft.")
                return render(request, "employees/add_employee.html", {"form": form})

            # Update partial info
            employee.first_name = first_name
            employee.last_name = request.POST.get("last_name", "").strip() or None
            employee.email = email
            employee.phone = request.POST.get("phone", "").strip() or None
            employee.address = request.POST.get("address", "").strip() or None
            employee.designation = request.POST.get("designation", "").strip() or None
            employee.package_per_annum = request.POST.get("package_per_annum") or None
            employee.package_per_month = request.POST.get("package_per_month") or None
            employee.is_draft = True
            employee.save()

            messages.info(request, "Draft updated successfully.")
            return redirect("employee_list")

        # --- Final Submission ---
        elif action == "final":
            if form.is_valid():
                emp = form.save(commit=False)
                emp.is_draft = False
                emp.save()
                messages.success(request, "Employee details updated successfully.")
                return redirect("employee_list")
            else:
                messages.error(request, "Please fix the form errors before final submission.")
    else:
        form = EmployeeForm(instance=employee)

    return render(request, "employees/add_employee.html", {"form": form})


# -------------------------------
# DELETE EMPLOYEE
# -------------------------------
def delete_employee(request, id):
    employee = get_object_or_404(Employee, id=id)
    employee.delete()
    messages.success(request, f"Employee {employee.first_name} {employee.last_name or ''} deleted successfully.")
    return redirect("employee_list")
def check_unique_employee(request):
    email = request.GET.get("email")
    phone = request.GET.get("phone")

    response = {"email_exists": False, "phone_exists": False}

    if email:
        response["email_exists"] = Employee.objects.filter(email__iexact=email).exists()

    if phone:
        response["phone_exists"] = Employee.objects.filter(phone__iexact=phone).exists()

    return JsonResponse(response)