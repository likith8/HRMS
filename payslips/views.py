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
import re

# 🪙 Format in Indian style (e.g., 2,40,000.00)
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
    error_message = None

    if request.method == "POST":
        based_on = request.POST.get("based_on")
        payslip_date = request.POST.get("payslip_date")
        days_worked = request.POST.get("days_worked")

        if not (based_on and payslip_date and days_worked):
            messages.error(request, "Please provide all required details.")
            return redirect("employee_list")

        try:
            date_obj = datetime.strptime(payslip_date, "%Y-%m-%d")
            month_year = date_obj.strftime("%B %Y")
            month_year_hyp = date_obj.strftime("%B-%Y")
            first_day = date_obj.replace(day=1)
            last_day = date_obj.replace(day=calendar.monthrange(date_obj.year, date_obj.month)[1])
            period = f"{first_day.strftime('%d/%m/%Y')} To {last_day.strftime('%d/%m/%Y')}"
        except ValueError:
            messages.error(request, "Invalid date format.")
            return redirect("employee_list")

        days_worked = int(days_worked)
        emp_code = None

        # ✅ Select salary source
        if based_on == "offer":
            if offer_letter and offer_letter.offer_date:
                if date_obj.date() < offer_letter.offer_date:
                    messages.error(request, f"Payslip date cannot be before the Offer Date ({offer_letter.offer_date.strftime('%d-%b-%Y')}).")
                    return redirect("employee_list")
            annual_package = getattr(employee, 'package_per_annum', Decimal('0.00'))
            emp_code=offer_letter.employee_code
            offer_ref = offer_letter
            hike_ref = None

        elif based_on == "hike":
            if hike_letter:
                annual_package = getattr(hike_letter, 'new_package', Decimal('0.00'))
                emp_code = hike_letter.employee_code
                offer_ref = None
                hike_ref = hike_letter

                # 🚫 Validation: Prevent payslip before hike_start_date
                if hike_letter.hike_start_date and date_obj.date() < hike_letter.hike_start_date:
                    messages.error(
                        request,
                        f"Payslip date ({date_obj.strftime('%d-%b-%Y')}) cannot be before hike start date "
                        f"({hike_letter.hike_start_date.strftime('%d-%b-%Y')})."
                    )
                    return redirect("employee_list")

            else:
                messages.error(request, "No hike letter found for this employee.")
                return redirect("employee_list")
        else:
            messages.error(request, "Invalid selection.")
            return redirect("employee_list")

        # ✅ Salary Breakdown (Monthly)
        monthly_ctc = (annual_package / Decimal(12)).quantize(Decimal('0.01'))

        basic_pct = Decimal('0.45')
        hra_pct = Decimal('0.225')
        conveyance = Decimal('1200.00')
        pf_employer = Decimal('0.00')
        variable_pay = Decimal('0.00')
        target_incentives = Decimal('0.00')

        salary_month = {
            'Basic': (monthly_ctc * basic_pct).quantize(Decimal('0.01')),
            'HRA': (monthly_ctc * hra_pct).quantize(Decimal('0.01')),
            'Conveyance': conveyance,
        }

        remaining = monthly_ctc - (salary_month['Basic'] + salary_month['HRA'] + conveyance)
        salary_month['Performance_Incentives'] = (remaining * Decimal('0.60')).quantize(Decimal('0.01'))
        salary_month['Special_Allowance'] = (remaining * Decimal('0.40')).quantize(Decimal('0.01'))
        salary_month['PF_Employer'] = pf_employer
        salary_month['Variable_Pay'] = variable_pay
        salary_month['Target_Incentives'] = target_incentives

        # ✅ Totals
        gross_salary = monthly_ctc
        per_day_salary = gross_salary / Decimal(30)
        gross_for_days = per_day_salary * Decimal(days_worked)
        deductions = Decimal('200.00')
        net_salary = gross_salary - deductions

        # ✅ Date of Joining format (e.g., 06ᵗʰ January, 2020)
        formatted_offer_date = None
        if offer_letter and offer_letter.offer_date:
            offer_date_new = offer_letter.offer_date
            day_int = offer_date_new.day
            if 10 <= day_int % 100 <= 20:
                suffix = "ᵀʰ"
            else:
                suffix = {1: "Sᵗ", 2: "ᴺᵈ", 3: "ᴿᵈ"}.get(day_int % 10, "ᵀʰ")
            formatted_offer_date = f"{day_int:02d}{suffix} {offer_date_new.strftime('%B, %Y')}"

        # ✅ Convert net salary to words
        net_salary_words = num2words(net_salary, lang='en_IN').title()
        if not net_salary_words.endswith("Only"):
            net_salary_words = f"{net_salary_words} Indian Rupees Only"

        # ✅ Save Payslip record
        payslip = Payslip.objects.create(
            employee=employee,
            based_on=based_on,
            offer_letter=offer_ref,
            hike_letter=hike_ref,
            month_year=month_year,
            days_worked=days_worked,
            gross_salary=gross_for_days,
            deductions=deductions,
            net_salary=net_salary
        )

        # ✅ Prepare context for Word document
        context = {
            'employee_name': f"{employee.first_name} {employee.last_name or ''}".strip(),
            'designation': employee.designation,
            'emp_code': emp_code,
            'monthyear': month_year,
            'monthyearhyp': month_year_hyp,
            'period': period,
            'days': days_worked,
            'date_of_joining': formatted_offer_date,

            # Salary Components (formatted)
            'Basic': indian_format(salary_month['Basic']),
            'HRA': indian_format(salary_month['HRA']),
            'Conveyance': indian_format(salary_month['Conveyance']),
            'Performance': indian_format(salary_month['Performance_Incentives']),
            'Special_Allowance': indian_format(salary_month['Special_Allowance']),
            'Total_Addition': indian_format(gross_salary),
            'Net_Salary': indian_format(net_salary),
            'Net_Salary_Words': net_salary_words,
        }

        # ✅ Generate Word Payslip
        template_path = os.path.join(settings.BASE_DIR, 'templates', 'payslip_template.docx')
        doc = DocxTemplate(template_path)
        doc.render(context)

        output_filename = f"payslip_{employee.first_name}{'_' + employee.last_name if employee.last_name else ''}_{month_year.replace(' ', '_')}.docx"
        output_path = os.path.join(settings.MEDIA_ROOT, 'payslips', output_filename)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except PermissionError:
                messages.error(request, "Close the open payslip file and try again.")
                return redirect('employee_list')

        doc.save(output_path)

        messages.success(request, f"Payslip for {employee.first_name} generated successfully!")
        return redirect("employee_list")

    return render(request, "payslips/generate_payslip.html", {
        "employee": employee,
        "offer_letter": offer_letter,
        "hike_letter": hike_letter,
        "error_message": error_message,
        "offer_start_date": offer_letter.offer_date.strftime("%Y-%m-%d") if offer_letter and offer_letter.offer_date else None,
        "hike_start_date": hike_letter.hike_start_date.strftime("%Y-%m-%d") if hike_letter and hike_letter.hike_start_date else None,
    })
