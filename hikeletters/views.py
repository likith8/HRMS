from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from decimal import Decimal
from datetime import datetime, date
import os
import re
from docxtpl import DocxTemplate

from employees.models import Employee
from hikeletters.models import HikeLetter
from offerletters.models import OfferLetter


# Get first day of next month
def get_first_day_of_next_month(input_date):
    year = input_date.year
    month = input_date.month
    if month == 12:
        return date(year + 1, 1, 1)
    else:
        return date(year, month + 1, 1)


# Convert number to Indian comma format
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


# Convert number to words (Lakhs/Crores)
def num_to_words(num):
    num = float(num)
    if num >= 10000000:
        value = num / 10000000
        return f"{value:.2f}".rstrip('0').rstrip('.') + " Crores Per Annum"
    elif num >= 100000:
        value = num / 100000
        return f"{value:.2f}".rstrip('0').rstrip('.') + " Lakhs Per Annum"
    else:
        value = num / 1000
        return f"{value:.2f}".rstrip('0').rstrip('.') + " Thousand Per Annum"


# Salary breakup calculation
def calculate_salary_breakup(per_annum):
    basic_pct = Decimal('0.45')
    hra_pct = Decimal('0.225')
    conveyance_amt = Decimal('14400')

    salary_annum = {
        'Basic': (per_annum * basic_pct).quantize(Decimal('0.01')),
        'HRA': (per_annum * hra_pct).quantize(Decimal('0.01')),
        'Conveyance': conveyance_amt,
    }

    perf_base = per_annum - (salary_annum['Basic'] + salary_annum['HRA'] + conveyance_amt)
    salary_annum['Performance_Incentives'] = (perf_base * Decimal('0.60')).quantize(Decimal('0.01'))
    salary_annum['Special_Allowance'] = (perf_base * Decimal('0.40')).quantize(Decimal('0.01'))

    return salary_annum


# Main View — Generate Hike Letter
def generate_hike_letter(request, employee_id):
    employee = get_object_or_404(Employee, id=employee_id)

    employee_name = f"{employee.first_name} {employee.last_name or ''}".strip()
    designation = employee.designation or ""
    old_package = getattr(employee, 'package_per_annum', Decimal('0.00'))

    # Get original offer letter
    offerletter = OfferLetter.objects.filter(employee=employee).first()
    if offerletter and offerletter.offer_date:
        employee_code = offerletter.employee_code
        original_joining_date = offerletter.offer_date
    else:
        employee_code = f"STPL{employee.id:03d}"
        original_joining_date = date.today()
    # Variable Pay from original offer letter
    old_variable_pay = Decimal('0.00')
    if offerletter and offerletter.variable_pay_per_annum:
        old_variable_pay = offerletter.variable_pay_per_annum.quantize(Decimal('0.01'))

    # Keep variable pay same during hike (standard practice)
    new_variable_pay = old_variable_pay
    # MIN DATE = Original joining date (NOT last hike)
    min_date = original_joining_date

    error_message = None

    if request.method == "POST":
        new_package_str = request.POST.get("new_package_annual")
        hr_input_date_str = request.POST.get("date")

        if not new_package_str or not hr_input_date_str:
            error_message = "Please provide both date and new package."
        else:
            try:
                new_package = Decimal(new_package_str)
                if new_package <= 0:
                    raise ValueError
            except:
                error_message = "Invalid package amount."
            else:
                try:
                    date_obj = datetime.strptime(hr_input_date_str, "%Y-%m-%d").date()
                except:
                    error_message = "Invalid date format."
                else:
                    # Only restriction: cannot be before original joining date
                    if date_obj < min_date:
                        error_message = f"Hike date cannot be before original joining date: {min_date.strftime('%d %B %Y')}"
                    else:
                        hike_start_date = get_first_day_of_next_month(date_obj)

                        # Always update/create — allows regeneration & corrections
                        hike_record, created = HikeLetter.objects.update_or_create(
                            employee=employee,
                            defaults={
                                'date': date_obj,
                                'hike_start_date': hike_start_date,
                                'employee_code': employee_code,
                                'old_package': old_package,
                                'new_package': new_package
                            }
                        )

                        # Generate DOCX
                        template_path = os.path.join("templates", "hike_letter_template.docx")
                        doc = DocxTemplate(template_path)


                        old_breakup = calculate_salary_breakup(old_package)
                        new_breakup = calculate_salary_breakup(new_package)
                        old_package_per_annum=old_package+old_variable_pay
                        new_package_per_annum=new_package+new_variable_pay

                        context = {
                            "date": date_obj.strftime("%d %B %Y"),
                            "employee_name": employee_name,
                            "employee_code": employee_code,
                            "designation": designation,
                            "hike_start_date": hike_start_date.strftime("%d %B %Y"),
                            "old_package": indian_format(old_package_per_annum),
                            "new_package": indian_format(new_package_per_annum),
                            "old_basic": indian_format(old_breakup['Basic']),
                            "old_hra": indian_format(old_breakup['HRA']),
                            "old_conveyance": indian_format(old_breakup['Conveyance']),
                            "old_perf": indian_format(old_breakup['Performance_Incentives']),
                            "old_special": indian_format(old_breakup['Special_Allowance']),
                            "new_basic": indian_format(new_breakup['Basic']),
                            "new_hra": indian_format(new_breakup['HRA']),
                            "new_conveyance": indian_format(new_breakup['Conveyance']),
                            "new_perf": indian_format(new_breakup['Performance_Incentives']),
                            "new_special": indian_format(new_breakup['Special_Allowance']),
                            "hike_month_year": hike_start_date.strftime("%B %Y"),
                            "new_package_words": num_to_words(new_package_per_annum),
                            "Variable_Pay_annum":indian_format(old_variable_pay),
                        }

                        doc.render(context)

                        output_dir = os.path.join("media", "hike_letters")
                        os.makedirs(output_dir, exist_ok=True)
                        safe_name = re.sub(r"[^\w]", "_", employee_name)
                        filename = f"{employee_name}_{employee_code}_hike_letter.docx"
                        output_path = os.path.join(output_dir, filename)

                        # Handle file lock
                        if os.path.exists(output_path):
                            try:
                                os.remove(output_path)
                            except PermissionError:
                                messages.error(request, "Previous hike letter is open. Close it and try again.")
                                return redirect(request.path)

                        try:
                            doc.save(output_path)
                        except PermissionError:
                            messages.error(request, "Cannot save: File is open in Word. Close it first.")
                            return redirect(request.path)

                        hike_record.hike_letter_file.name = output_path.replace("media/", "")
                        hike_record.save()

                        messages.success(request, f"Hike letter generated successfully for {employee_name}!")
                        return redirect('employee_list')

    # GET request
    return render(request, "hikeletters/hike_letter.html", {
        "employee": employee,
        "old_package": old_package,
        "designation": designation,
        "error_message": error_message,
        "min_date": min_date,  # This is now original offer date
    })