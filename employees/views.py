from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.urls import reverse
from .models import Employee
from .forms import EmployeeForm
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
import pandas as pd
from datetime import datetime

# -------------------------------
# ADD EMPLOYEE
# -------------------------------
@login_required
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
            return redirect(reverse("employees:employee_list"))

        # --- Final Submission ---
        elif action == "final":
            if form.is_valid():
                email = form.cleaned_data.get('email')
                phone = form.cleaned_data.get('phone')

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
                    return redirect(reverse("employees:employee_list"))
            else:
                messages.error(request, "Please correct the highlighted errors before final submission.")
    else:
        form = EmployeeForm()

    return render(request, "employees/add_employee.html", {"form": form})


# -------------------------------
# LIST EMPLOYEES
# -------------------------------
@login_required
def employee_list(request):
    employees = Employee.objects.all().order_by("-created_at")

    if request.method == "POST":
        search_value = request.POST.get("search", "").strip()
        if search_value:
            by_code = employees.filter(employee_code__icontains=search_value)
            by_phone = employees.filter(phone__icontains=search_value)
            employees = by_code | by_phone

    return render(request, "employees/employee_list.html", {"employees": employees})


# -------------------------------
# EDIT EMPLOYEE
# -------------------------------
@login_required
def edit_employee(request, id):
    employee = get_object_or_404(Employee, id=id)

    if request.method == "POST":
        form = EmployeeForm(request.POST, instance=employee)
        action = request.POST.get("action")

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
            return redirect(reverse("employees:employee_list"))

        elif action == "final":
            if form.is_valid():
                emp = form.save(commit=False)
                emp.is_draft = False
                emp.save()
                messages.success(request, "Employee details updated successfully.")
                return redirect(reverse("employees:employee_list"))
            else:
                messages.error(request, "Please fix the form errors before final submission.")
    else:
        form = EmployeeForm(instance=employee)

    return render(request, "employees/add_employee.html", {"form": form})


# -------------------------------
# DELETE EMPLOYEE
# -------------------------------
@login_required
def delete_employee(request, id):
    employee = get_object_or_404(Employee, id=id)
    employee.delete()
    messages.success(request, f"Employee {employee.first_name} {employee.last_name or ''} deleted successfully.")
    return redirect(reverse("employees:employee_list"))


# -------------------------------
# CHECK UNIQUE EMPLOYEE
# -------------------------------
@login_required
def check_unique_employee(request):
    email = request.GET.get("email")
    phone = request.GET.get("phone")

    response = {"email_exists": False, "phone_exists": False}

    if email:
        response["email_exists"] = Employee.objects.filter(email__iexact=email).exists()

    if phone:
        response["phone_exists"] = Employee.objects.filter(phone__iexact=phone).exists()

    return JsonResponse(response)


# -------------------------------
# EMPLOYEE MASTER REPORT (EXCEL)
# -------------------------------
@login_required
def employee_master_report(request):
    employees = Employee.objects.all().prefetch_related(
        'offerletter_set', 'hike_letters', 'releaving_letters'
    ).order_by('-created_at')

    COLUMN_MAPPING = [
        ("emp_code", "Emp Code"),
        ("full_name", "Full Name"),
        ("email", "Email"),
        ("phone", "Phone"),
        ("designation", "Designation"),
        ("ctc_annual", "CTC (Annual)"),
        ("ctc_monthly", "CTC (Monthly)"),
        ("offer_date", "Offer Date"),
        ("latest_hike", "Latest Hike"),
        ("hike_date", "Hike Date"),
        ("relieving_date", "Relieving Date"),
        ("status", "Status"),
        ("created", "Created"),
    ]

    data = []
    for emp in employees:
        offer = emp.offerletter_set.last()
        hike = emp.hike_letters.last() if hasattr(emp, 'hike_letters') and emp.hike_letters.exists() else None
        rel = emp.releaving_letters.last() if hasattr(emp, 'releaving_letters') else None

        full_name = f"{emp.first_name or ''} {emp.last_name or ''}".strip() or "—"
        original_ctc = emp.package_per_annum or 0
        ctc_annual_display = f"₹{original_ctc:,.0f}"
        ctc_monthly_display = f"₹{original_ctc / 12:,.0f}" if original_ctc else "₹0"
        latest_hike_amount = "-"
        hike_date_str = "-"

        if hike and hike.new_package:
            latest_hike_amount = f"₹{hike.new_package:,.0f}"
            hike_date_str = hike.date.strftime("%d-%b-%Y") if hike.date else "-"

        offer_date = offer.offer_date.strftime("%d-%b-%Y") if offer and offer.offer_date else "-"
        relieving_date = rel.releaving_date.strftime("%d-%b-%Y") if rel and rel.releaving_date else "-"
        placed_in = rel.placed_in_company if rel and rel.placed_in_company else "-"

        status = "Draft" if getattr(emp, 'is_draft', False) else "Active"
        if rel:
            status = f"Relieved to {placed_in}" if placed_in != "-" else "Relieved"

        data.append({
            "emp_code": emp.employee_code or "-",
            "full_name": full_name,
            "email": emp.email or "-",
            "phone": emp.phone or "-",
            "designation": emp.designation or "-",
            "ctc_annual": ctc_annual_display,
            "ctc_monthly": ctc_monthly_display,
            "offer_date": offer_date,
            "latest_hike": latest_hike_amount,
            "hike_date": hike_date_str,
            "relieving_date": relieving_date,
            "status": status,
            "created": emp.created_at.strftime("%d-%b-%Y %I:%M %p"),
        })

    # Excel download
    if request.GET.get('download'):
        df = pd.DataFrame(data)
        df = df[[key for key, _ in COLUMN_MAPPING]]
        df.columns = [label for _, label in COLUMN_MAPPING]

        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response['Content-Disposition'] = f'attachment; filename="Employee_Master_{datetime.now().strftime("%Y%m%d_%H%M")}.xlsx"'

        with pd.ExcelWriter(response, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name="Employees", index=False)
            worksheet = writer.sheets["Employees"]
            for i, col in enumerate(df.columns, 1):
                max_len = max(df[col].astype(str).map(len).max(), len(col)) + 5
                worksheet.column_dimensions[worksheet.cell(row=1, column=i).column_letter].width = min(max_len, 50)

        return response

    return render(request, 'employees/master_report.html', {'employees': data, 'total': len(data)})
