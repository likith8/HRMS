from django.shortcuts import render, get_object_or_404, redirect
from employees.models import Employee
from offerletters.models import OfferLetter
from hikeletters.models import HikeLetter
from .models import ReleavingLetter
from docxtpl import DocxTemplate
from django.conf import settings
import os
from datetime import datetime
from django.contrib import messages


def generate_releaving(request, employee_id):
    employee = get_object_or_404(Employee, id=employee_id)
    offer_letter = OfferLetter.objects.filter(employee=employee).last()
    hike_letter = HikeLetter.objects.filter(employee=employee).last()

    if not offer_letter:
        messages.error(request, "Cannot generate releaving letter: No offer letter found for this employee.")
        return redirect("employee_list")

    if request.method == "POST":
        releaving_date = request.POST.get("releaving_date")

        if not releaving_date:
            messages.error(request, "Please select a valid releaving date.")
            return render(request, "releaving/generate.html", {
                "employee": employee,
                "offer_letter": offer_letter,
                "hike_letter": hike_letter,
            })

        # Convert and validate releaving date
        date_obj = datetime.strptime(releaving_date, "%Y-%m-%d").date()
        offer_date_obj = offer_letter.offer_date

        if date_obj < offer_date_obj:
            messages.error(request, f"Releaving date cannot be before the offer date ({offer_date_obj.strftime('%d-%m-%Y')}).")
            return render(request, "releaving/generate.html", {
                "employee": employee,
                "offer_letter": offer_letter,
                "hike_letter": hike_letter,
            })

        # Format releaving date
        day_int = date_obj.day
        weekday_name = date_obj.strftime("%A")
        suffix = "ᵀʰ" if 10 <= day_int % 100 <= 20 else {1: "Sᵗ", 2: "ᴺᵈ", 3: "ᴿᵈ"}.get(day_int % 10, "ᵀʰ")
        formatted_releaving_date = f"{day_int:02d}{suffix} {date_obj.strftime('%B, %Y')}"

        # Format offer date
        offer_day_int = offer_date_obj.day
        offer_suffix = "ᵀʰ" if 10 <= offer_day_int % 100 <= 20 else {1: "Sᵗ", 2: "ᴺᵈ", 3: "ᴿᵈ"}.get(offer_day_int % 10, "ᵀʰ")
        formatted_offer_date = f"{offer_day_int:02d}{offer_suffix} {offer_date_obj.strftime('%B, %Y')}"

        # Save to database
        releaving = ReleavingLetter.objects.create(
            employee=employee,
            releaving_date=date_obj
        )

        # Prepare context for Word doc
        context = {
            "employee_first_name": employee.first_name,
            "employee_name": f"{employee.first_name} {employee.last_name or ''}".strip(),
            "designation": employee.designation,
            "emp_code": offer_letter.employee_code,
            "offer_date": formatted_offer_date,
            "releaving_date": formatted_releaving_date,
            "releaving_day": weekday_name,
        }

        # Load and render Word template
        template_path = os.path.join(settings.BASE_DIR, "templates", "releaving_letter.docx")
        doc = DocxTemplate(template_path)

        doc.render(context)

        output_filename = f"Releaving_{employee.first_name}{'_' + employee.last_name if employee.last_name else ''}.docx"
        output_path = os.path.join(settings.MEDIA_ROOT, "releaving", output_filename)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        try:
            doc.save(output_path)
            messages.success(request, f"Releaving Letter for {employee.first_name} generated successfully!")
            return redirect("employee_list")
        except PermissionError:
            messages.error(request, f"Cannot save the file. Please close '{output_filename}' if it is open and try again.")
            return render(request, "releaving/generate.html", {
                "employee": employee,
                "offer_letter": offer_letter,
                "hike_letter": hike_letter,
            })

    # GET request
    return render(request, "releaving/generate.html", {
        "employee": employee,
        "offer_letter": offer_letter,
        "hike_letter": hike_letter,
    })
