from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.conf import settings
from django.http import FileResponse, Http404
from docxtpl import DocxTemplate
from employees.models import Employee
from offerletters.models import OfferLetter
from hikeletters.models import HikeLetter
from .models import ReleavingLetter
import os
from datetime import datetime


def generate_releaving(request, employee_id):
    employee = get_object_or_404(Employee, id=employee_id)
    offer_letter = OfferLetter.objects.filter(employee=employee).last()
    hike_letter = HikeLetter.objects.filter(employee=employee).last()

    if not offer_letter:
        messages.error(request, "Cannot generate relieving letter: No offer letter found.")
        return redirect("employee_list")

    employee_name = f"{employee.first_name} {employee.last_name or ''}".strip()

    if request.method == "POST":
        releaving_date_str = request.POST.get("releaving_date")
        placed_in_company = request.POST.get("placed_in_company", "").strip()

        if not releaving_date_str:
            messages.error(request, "Please select relieving date.")
            return redirect(request.path)

        try:
            releaving_date = datetime.strptime(releaving_date_str, "%Y-%m-%d").date()
        except ValueError:
            messages.error(request, "Invalid date format.")
            return redirect(request.path)

        # -------------------------------------------
        # Block: relieving cannot be before offer date
        # -------------------------------------------
        if releaving_date < offer_letter.offer_date:
            messages.error(request,
                f"Relieving date cannot be before joining date ({offer_letter.offer_date.strftime('%d %B %Y')})."
            )
            return redirect(request.path)

        # -------------------------------------------
        # Update or create relieving letter entry
        # -------------------------------------------
        relieving_obj, created = ReleavingLetter.objects.update_or_create(
            employee=employee,
            defaults={
                "releaving_date": releaving_date,
                "placed_in_company": placed_in_company or None,
            }
        )

        # -------------------------------------------
        # Generate Word Document
        # -------------------------------------------
        template_path = os.path.join(settings.BASE_DIR, "templates", "releaving_letter.docx")
        if not os.path.exists(template_path):
            messages.error(request, "Template file missing: releaving_letter.docx")
            return redirect("employee_list")

        # Format dates
        def format_date(date_obj):
            day = date_obj.day
            suffix = "th" if 11 <= day % 100 <= 13 else {1:"st",2:"nd",3:"rd"}.get(day % 10,"th")
            return f"{day}{suffix} {date_obj.strftime('%B %Y')}"

        formatted_offer_date = format_date(offer_letter.offer_date)
        formatted_releaving_date = format_date(releaving_date)
        weekday_name = releaving_date.strftime("%A")

        context = {
            "employee_first_name": employee.first_name,
            "employee_name": employee_name,
            "designation": employee.designation or "N/A",
            "emp_code": offer_letter.employee_code or "N/A",
            "offer_date": formatted_offer_date,
            "releaving_date": formatted_releaving_date,
            "releaving_day": weekday_name,
            "placed_in_company": placed_in_company or "",
            "has_placed_company": bool(placed_in_company),
        }

        doc = DocxTemplate(template_path)
        doc.render(context)

        # -------------------------------------------
        # Save file into MEDIA/releaving_letters/
        # -------------------------------------------
        safe_name = employee_name.replace(" ", "_")
        filename = f"Relieving_{offer_letter.employee_code}_{safe_name}.docx"
        output_dir = os.path.join(settings.MEDIA_ROOT, "releaving_letters")
        os.makedirs(output_dir, exist_ok=True)
        file_path = os.path.join(output_dir, filename)

        # Delete old file if exists
        if relieving_obj.letter_file and os.path.exists(relieving_obj.letter_file.path):
            try:
                os.remove(relieving_obj.letter_file.path)
            except PermissionError:
                messages.error(request, "Close the previously opened letter in Word and try again.")
                return redirect(request.path)

        # Save new file
        doc.save(file_path)
        relieving_obj.letter_file.name = f"releaving_letters/{filename}"
        relieving_obj.save()

        messages.success(request, "Relieving letter generated successfully.")
        return redirect("generate_releaving", employee_id=employee.id)

    # GET Request
    relieving_obj = ReleavingLetter.objects.filter(employee=employee).last()

    return render(request, "releaving/generate.html", {
        "employee": employee,
        "offer_letter": offer_letter,
        "hike_letter": hike_letter,
        "relieving_obj": relieving_obj,
    })


# ---------------------------------------------------------
# DOWNLOAD FUNCTION
# ---------------------------------------------------------
def download_releaving_letter(request, employee_id):
    employee = get_object_or_404(Employee, id=employee_id)
    relieving = ReleavingLetter.objects.filter(employee=employee).last()

    if not relieving or not relieving.letter_file:
        raise Http404("No relieving letter found for this employee.")

    file_path = relieving.letter_file.path
    if not os.path.exists(file_path):
        raise Http404("File missing.")

    return FileResponse(open(file_path, "rb"), as_attachment=True, filename=os.path.basename(file_path))
