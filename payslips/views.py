# payslips/views.py  ← CLEAN & CORRECTED VERSION

from django.shortcuts import render, get_object_or_404, redirect
from django.conf import settings
from django.contrib import messages
from decimal import Decimal
from datetime import datetime
from employees.models import Employee
from offerletters.models import OfferLetter
from hikeletters.models import HikeLetter
from .models import Payslip
from docxtpl import DocxTemplate
from num2words import num2words
import os
import calendar


def indian_format(amount):
    try:
        amount = float(amount)
    except:
        return amount
    s, d = f"{amount:.2f}".split(".")
    if len(s) > 3:
        int_part = s[-3:]
        s = s[:-3]
        parts = []
        while len(s) > 2:
            parts.append(s[-2:])
            s = s[:-2]
        if s:
            parts.append(s)
        parts.reverse()
        int_part = ",".join(parts) + "," + int_part
    else:
        int_part = s
    return f"{int_part}.{d}"


def generate_payslip(request, employee_id):
    employee = get_object_or_404(Employee, id=employee_id)
    offer_letter = OfferLetter.objects.filter(employee=employee).last()
    hike_letter = HikeLetter.objects.filter(employee=employee).last()

    if request.method == "POST":
        based_on = request.POST.get("based_on")
        payslip_date = request.POST.get("payslip_date")
        days_worked = request.POST.get("days_worked")

        if not all([based_on, payslip_date, days_worked]):
            messages.error(request, "Please fill all fields.")
            return redirect(request.path)

        try:
            date_obj = datetime.strptime(payslip_date, "%Y-%m-%d")
            month_year = date_obj.strftime("%B %Y")
        except ValueError:
            messages.error(request, "Invalid date.")
            return redirect(request.path)

        days_worked = int(days_worked)

        # Salary source logic
        if based_on == "offer":
            if offer_letter and offer_letter.offer_date and date_obj.date() < offer_letter.offer_date:
                messages.error(request, "Date cannot be before offer date.")
                return redirect(request.path)

            annual_package = getattr(employee, 'package_per_annum', Decimal('0'))
            offer_ref = offer_letter
            hike_ref = None

        elif based_on == "hike":
            if not hike_letter:
                messages.error(request, "No hike letter found.")
                return redirect(request.path)

            annual_package = hike_letter.new_package or Decimal('0')
            offer_ref = None
            hike_ref = hike_letter

            if hike_letter.hike_start_date and date_obj.date() < hike_letter.hike_start_date:
                messages.error(request, "Date cannot be before hike start date.")
                return redirect(request.path)
        else:
            messages.error(request, "Invalid selection.")
            return redirect(request.path)

        # Salary calculation
        monthly = (annual_package / 12).quantize(Decimal('0.01'))
        basic = (monthly * Decimal('0.45')).quantize(Decimal('0.01'))
        hra = (monthly * Decimal('0.225')).quantize(Decimal('0.01'))
        conveyance = Decimal('1200')
        remaining = monthly - basic - hra - conveyance
        performance = (remaining * Decimal('0.60')).quantize(Decimal('0.01'))
        special = (remaining * Decimal('0.40')).quantize(Decimal('0.01'))
        gross_salary = monthly
        net_salary = gross_salary - Decimal('200')

        # STORE FULL SALARY (NO PRORATION)
        payslip, created = Payslip.objects.update_or_create(
            employee=employee,
            month_year=month_year,
            defaults={
                'based_on': based_on,
                'offer_letter': offer_ref,
                'hike_letter': hike_ref,
                'days_worked': days_worked,
                'gross_salary': gross_salary,     # FULL salary
                'deductions': Decimal('200'),
                'net_salary': net_salary,         # FULL net salary
            }
        )

        # Generate document
        context = {
            'employee_name': f"{employee.first_name} {employee.last_name}".strip(),
            'designation': employee.designation or "N/A",
            'emp_code': (
                offer_letter.employee_code if based_on == "offer"
                else hike_letter.employee_code
            ) if offer_letter or hike_letter else "N/A",
            'monthyear': month_year,
            'monthyearhyp': month_year.replace(" ", "-"),
            'period': f"01/{date_obj.month:02d}/{date_obj.year} To "
                      f"{calendar.monthrange(date_obj.year, date_obj.month)[1]:02d}/{date_obj.month:02d}/{date_obj.year}",
            'days': days_worked,
            'date_of_joining': offer_letter.offer_date.strftime("%d %B %Y") if offer_letter and offer_letter.offer_date else "",
            'Basic': indian_format(basic),
            'HRA': indian_format(hra),
            'Conveyance': indian_format(conveyance),
            'Performance': indian_format(performance),
            'Special_Allowance': indian_format(special),
            'Total_Addition': indian_format(gross_salary),
            'Net_Salary': indian_format(net_salary),
            'Net_Salary_Words': num2words(int(net_salary), lang='en_IN').title() + " Rupees Only",
        }

        template_path = os.path.join(settings.BASE_DIR, 'templates', 'payslip_template.docx')
        doc = DocxTemplate(template_path)
        doc.render(context)

        filename = f"Payslip_{employee.first_name}_{employee.last_name}_{month_year.replace(' ', '_')}.docx"
        filepath = os.path.join(settings.MEDIA_ROOT, 'payslips', filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except PermissionError:
                messages.error(request, "Close the open file and try again.")
                return redirect(request.path)

        doc.save(filepath)

        payslip.payslip_file.name = f"payslips/{filename}"
        payslip.save(update_fields=['payslip_file'])

        if payslip.payslip_file:
            payslip.payslip_file.close()
            payslip.payslip_file = payslip.payslip_file

        messages.success(request, f"Payslip for {month_year} generated successfully!")
        return redirect(request.path + f"?month={date_obj.strftime('%Y-%m')}")

    # GET request
    payslip_obj = None
    file_exists = False

    if request.GET.get("month"):
        selected = request.GET.get("month")
        payslip_obj = Payslip.objects.filter(employee=employee, month_year=selected).first()
    else:
        payslip_obj = Payslip.objects.filter(employee=employee).order_by('-created_at').first()

    if payslip_obj and payslip_obj.payslip_file:
        file_exists = os.path.exists(payslip_obj.payslip_file.path)

    payslips_list = Payslip.objects.filter(employee=employee).order_by('-created_at')

    return render(request, "payslips/generate_payslip.html", {
        "employee": employee,
        "offer_letter": offer_letter,
        "hike_letter": hike_letter,
        "payslip_obj": payslip_obj,
        "file_exists": file_exists,
        "offer_start_date": offer_letter.offer_date.strftime("%Y-%m-%d") if offer_letter and offer_letter.offer_date else None,
        "hike_start_date": hike_letter.hike_start_date.strftime("%Y-%m-%d") if hike_letter and hike_letter.hike_start_date else None,
        "payslips_list": payslips_list,
        "Net_Salary":indian_format(payslip_obj.net_salary) if payslip_obj else None,
    })
