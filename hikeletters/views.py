from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from decimal import Decimal
from datetime import datetime, date
import os
from docxtpl import DocxTemplate

from employees.models import Employee
from hikeletters.models import HikeLetter
from offerletters.models import OfferLetter

from calendar import monthrange


# ➤ Get first day of next month
def get_first_day_of_next_month(input_date):
    year = input_date.year
    month = input_date.month

    if month == 12:
        return date(year + 1, 1, 1)
    else:
        return date(year, month + 1, 1)


def get_day_suffix(day):
    superscripts = {1: "ˢᵗ", 2: "ⁿᵈ", 3: "ʳᵈ"}
    if 10 <= day % 100 <= 20:
        return "ᵗʰ"
    return superscripts.get(day % 10, "ᵗʰ")


# ➤ Convert number to Indian comma format
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


# ➤ Convert number to words
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


# ➤ Salary breakup calculation
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



# ➤ Main View — Generate Hike Letter
def generate_hike_letter(request, employee_id):

    employee = get_object_or_404(Employee, id=employee_id)

    employee_name = f"{employee.first_name} {employee.last_name or ''}"
    designation = employee.designation or ""
    old_package = getattr(employee, 'package_per_annum', Decimal('0.00'))

    # Get latest offer letter
    offerletter = OfferLetter.objects.filter(employee=employee).last()
    if offerletter:
        employee_code = offerletter.employee_code
        offer_start_date = offerletter.offer_date
    else:
        employee_code = f"STPL{employee.id:03d}"
        offer_start_date = datetime.today().date()

    # Last hike date
    last_hike = employee.hike_letters.order_by('-hike_start_date').first()
    if last_hike:
        min_date = last_hike.hike_start_date
    else:
        min_date = offer_start_date

    error_message = None

    if request.method == "POST":
        new_package_str = request.POST.get("new_package_annual")
        hr_input_date = request.POST.get("date")

        if not new_package_str or not hr_input_date:
            error_message = "Please provide date and new package."
        else:
            new_package = Decimal(new_package_str)
            date_obj = datetime.strptime(hr_input_date, "%Y-%m-%d").date()

            if date_obj < min_date:
                error_message = f"Hike date cannot be before {min_date}"
            else:
                hike_start_date = get_first_day_of_next_month(date_obj)

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

                # Build DOCX file
                template_path = os.path.join("templates", "hike_letter_template.docx")
                doc = DocxTemplate(template_path)

                old_breakup = calculate_salary_breakup(old_package)
                new_breakup = calculate_salary_breakup(new_package)

                hike_month_year = hike_start_date.strftime("%B %Y")

                context = {
                    "date": date_obj.strftime("%d %B %Y"),
                    "employee_name": employee_name,
                    "employee_code": employee_code,
                    "designation": designation,
                    "hike_start_date": hike_start_date.strftime("%d %B %Y"),
                    "old_package": indian_format(old_package),
                    "new_package": indian_format(new_package),
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
                    "hike_month_year": hike_month_year,
                    "new_package_words": num_to_words(new_package),
                }

                doc.render(context)

                output_dir = os.path.join("media", "hike_letters")
                os.makedirs(output_dir, exist_ok=True)
                output_path = os.path.join(output_dir, f"{employee_name}_{employee_code}_hike_letter.docx")

                # ---- CHECK IF OLD HIKE LETTER IS OPEN (Windows file lock) ----
                if os.path.exists(output_path):
                    try:
                        test = open(output_path, "wb")
                        test.close()
                    except PermissionError:
                        messages.error(request, "Old hike letter is OPENED. Please close it and try again.")
                        return redirect(request.path)

                # ---- TRY SAVING FILE ----
                try:
                    doc.save(output_path)
                except PermissionError:
                    messages.error(request, "Old hike letter is OPENED. Please close it and try again.")
                    return redirect(request.path)

                hike_record.hike_letter_file.name = output_path.replace("media/", "")
                hike_record.save()

                messages.success(request, "Hike generated Successfully!")
                return redirect('employee_list')

    return render(request, "hikeletters/hike_letter.html", {
        "employee": employee,
        "old_package": old_package,
        "designation": designation,
        "error_message": error_message,
        "min_date": min_date,
    })
