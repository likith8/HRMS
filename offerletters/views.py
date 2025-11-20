# offerletters/views.py — FINAL PERFECT VERSION (Everything Fixed)
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.conf import settings
from employees.models import Employee
from .models import OfferLetter
from docxtpl import DocxTemplate
from decimal import Decimal
from num2words import num2words
import os
import re
from datetime import datetime


def indian_format(amount):
    """Indian currency format: 240000 → 2,40,000.00"""
    try:
        amount = float(amount)
    except:
        return "0.00"
    s, d = f"{amount:.2f}".split(".")
    if len(s) <= 3:
        return f"{s}.{d}"
    int_part = s[-3:]
    s = s[:-3]
    parts = []
    while len(s) > 2:
        parts.append(s[-2:])
        s = s[:-2]
    if s:
        parts.append(s)
    parts.reverse()
    return f"{','.join(parts) + ',' + int_part}.{d}"


def get_next_global_series():
    """Get highest valid series number from clean STPL codes only"""
    highest = 0
    for offer in OfferLetter.objects.exclude(employee_code__isnull=True).exclude(employee_code=""):
        code = str(offer.employee_code or "").strip()
        if code.startswith("STPL") and len(code) >= 11:
            series_part = code[8:]  # After STPLMMYY
            if series_part.isdigit():
                num = int(series_part)
                if num > highest:
                    highest = num
    return highest + 1


def generate_offer_letter(request, employee_id):
    employee = get_object_or_404(Employee, id=employee_id)

    if request.method != "POST":
        messages.error(request, "Invalid request.")
        return redirect("employee_list")

    offer_date_str = request.POST.get("offer_date")
    code_mode = request.POST.get("code_mode", "auto")
    final_code = request.POST.get("final_employee_code", "").strip().upper()

    if not offer_date_str:
        messages.error(request, "Please select offer date.")
        return redirect("employee_list")

    try:
        offer_date = datetime.strptime(offer_date_str, "%Y-%m-%d").date()
    except:
        messages.error(request, "Invalid date format.")
        return redirect("employee_list")

    # Format date: 20th November, 2025
    day = offer_date.day
    suffix = "th" if 11 <= day <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    formatted_date = f"{day}{suffix} {offer_date.strftime('%B, %Y')}"

    mm = offer_date.strftime("%m")
    yy = offer_date.strftime("%y")
    prefix = f"STPL{mm}{yy}"

    # ===================================================================
    # CHECK IF EMPLOYEE ALREADY HAS A CODE → KEEP IT ON RE-GENERATION
    # ===================================================================
    existing_offer = OfferLetter.objects.filter(employee=employee).first()
    employee_code = None

    if existing_offer and existing_offer.employee_code:
        old_code = str(existing_offer.employee_code).strip()
        if old_code.startswith("STPL"):
            employee_code = old_code
            messages.info(request, f"Re-generating offer letter. Using existing code: {employee_code}")
        # else: corrupted → generate new

    # If no valid existing code → generate new
    if not employee_code:
        if code_mode == "manual":
            if not final_code:
                messages.error(request, "Enter employee code in manual mode.")
                return redirect("employee_list")
            if not final_code.startswith(prefix):
                messages.error(request, f"Code must start with {prefix}")
                return redirect("employee_list")
            series_part = final_code[8:]
            if not series_part.isdigit():
                messages.error(request, "Invalid series number.")
                return redirect("employee_list")
            if OfferLetter.objects.filter(employee_code__endswith=series_part).exists():
                messages.error(request, f"Series {series_part} already used.")
                return redirect("employee_list")
            employee_code = final_code

        else:
            # AUTO MODE — clean & safe
            next_series = get_next_global_series()
            if next_series < 1000:
                series_str = f"{next_series:03d}"
            else:
                series_str = str(next_series)
            employee_code = f"{prefix}{series_str}"

    # ===================================================================
    # FULL SALARY BREAKUP (Your Original Logic — Preserved 100%)
    # ===================================================================
    try:
        per_month = Decimal(employee.package_per_month or 0)
    except:
        per_month = (Decimal(getattr(employee, "package_per_annum", 0) or 0) / 12).quantize(Decimal("0.01"))
    per_annum = (per_month * 12).quantize(Decimal("0.01"))

    basic_pct = Decimal("0.45")
    hra_pct = Decimal("0.225")
    conveyance_annum = Decimal("14400")
    pf_employer = Decimal("0.00")
    variable_pay = Decimal("0.00")
    target_incentives = Decimal("0.00")

    # Annual
    basic_annum = (per_annum * basic_pct).quantize(Decimal("0.01"))
    hra_annum = (per_annum * hra_pct).quantize(Decimal("0.01"))
    remaining_annum = per_annum - basic_annum - hra_annum - conveyance_annum
    perf_incentives_annum = (remaining_annum * Decimal("0.60")).quantize(Decimal("0.01"))
    special_allowance_annum = (remaining_annum * Decimal("0.40")).quantize(Decimal("0.01"))

    total_ctc_annum = per_annum

    # Monthly
    basic_month = (basic_annum / 12).quantize(Decimal("0.01"))
    hra_month = (hra_annum / 12).quantize(Decimal("0.01"))
    conveyance_month = (conveyance_annum / 12).quantize(Decimal("0.01"))
    remaining_month = per_month - basic_month - hra_month - conveyance_month
    perf_incentives_month = (remaining_month * Decimal("0.60")).quantize(Decimal("0.01"))
    special_allowance_month = (remaining_month * Decimal("0.40")).quantize(Decimal("0.01"))

    # Words
    try:
        total_ctc_words = num2words(int(total_ctc_annum), lang="en_IN").title()
        total_ctc_words = re.sub(r"\s+", " ", total_ctc_words.replace(",", "")) + " Indian Rupees Only"
    except:
        total_ctc_words = ""

    # ===================================================================
    # RENDER DOCX TEMPLATE
    # ===================================================================
    template_path = os.path.join(settings.BASE_DIR, "templates", "offer_template.docx")
    if not os.path.exists(template_path):
        messages.error(request, "Offer template not found.")
        return redirect("employee_list")

    doc = DocxTemplate(template_path)

    address_lines = [line.strip() for line in str(getattr(employee, "address", "")).splitlines() if line.strip()]
    formatted_address = "<w:br/>".join(address_lines) if address_lines else ""

    context = {
        "date": formatted_date,
        "first_name": employee.first_name,
        "last_name": employee.last_name or "",
        "address": formatted_address,
        "designation": employee.designation or "",
        "package_per_month": indian_format(per_month),
        "package_per_annum": indian_format(per_annum),
        "Basic_annum": indian_format(basic_annum),
        "HRA_annum": indian_format(hra_annum),
        "Conveyance_annum": indian_format(conveyance_annum),
        "Performance_Incentives_annum": indian_format(perf_incentives_annum),
        "Special_Allowance_annum": indian_format(special_allowance_annum),
        "PF_Employer_annum": indian_format(pf_employer),
        "Variable_Pay_annum": indian_format(variable_pay),
        "Target_Incentives_annum": indian_format(target_incentives),
        "Basic_month": indian_format(basic_month),
        "HRA_month": indian_format(hra_month),
        "Conveyance_month": indian_format(conveyance_month),
        "Performance_Incentives_month": indian_format(perf_incentives_month),
        "Special_Allowance_month": indian_format(special_allowance_month),
        "Total_CTC_annum": indian_format(total_ctc_annum),
        "Total_CTC_month": indian_format(per_month),
        "Total_CTC_words": total_ctc_words,
        "employee_code": employee_code,
    }

    try:
        doc.render(context)
    except Exception as e:
        messages.error(request, f"Template error: {e}")
        return redirect("employee_list")

    # ===================================================================
    # SAVE FILE
    # ===================================================================
    safe_name = re.sub(r"[^\w]", "_", f"{employee.first_name}_{employee.last_name or ''}".strip())
    filename = f"Offer_{employee_code}_{safe_name}.docx"
    output_dir = os.path.join(settings.MEDIA_ROOT, "offer_letters")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, filename)

    if os.path.exists(output_path):
        try:
            os.remove(output_path)
        except:
            messages.error(request, "File is open. Close it and try again.")
            return redirect("employee_list")

    try:
        doc.save(output_path)
    except Exception as e:
        messages.error(request, f"Save failed: {e}")
        return redirect("employee_list")

    # ===================================================================
    # SAVE TO DATABASE
    # ===================================================================
    OfferLetter.objects.update_or_create(
        employee=employee,
        defaults={
            "offer_date": offer_date,
            "employee_code": employee_code,
            "file": f"offer_letters/{filename}"
        }
    )

    if hasattr(employee, 'employee_code'):
        employee.employee_code = employee_code
        employee.save(update_fields=['employee_code'])

    action = "Re-generated" if existing_offer and existing_offer.employee_code else "Generated"
    messages.success(request, f"Offer letter {action.lower()} successfully: {employee_code}")
    return redirect("employee_list")