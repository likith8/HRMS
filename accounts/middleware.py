from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from django.conf import settings
import time
from django.contrib.auth import logout

class AuthRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Resolve allowed URLs dynamically
        allowed_prefixes = [
            reverse("accounts:login"),
            reverse("accounts:logout"),
            "/",
        ]

        path = request.path
        is_allowed = any(path.startswith(prefix) for prefix in allowed_prefixes)

        if request.user.is_authenticated:
            last_activity = request.session.get("last_activity")
            current_time = time.time()
            timeout = getattr(settings, "SESSION_TIMEOUT", None)

            if timeout and last_activity and (current_time - last_activity > timeout):
                messages.warning(request, "Your session has expired due to inactivity.")
                logout(request)
                return redirect("accounts:login")

            request.session["last_activity"] = current_time

        elif not is_allowed:
            return redirect("accounts:login")

        return self.get_response(request)
