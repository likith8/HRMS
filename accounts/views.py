from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test

# --- Admin Check ---
def admin_required(user):
    return user.is_superuser

def home(request):
    return render(request, 'accounts/home.html')

# --- Dashboard ---
@login_required
def dashboard_view(request):
    return render(request, "accounts/dashboard.html", {
        "user": request.user
    })

# --- Login View ---
def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username").strip()
        password = request.POST.get("password").strip()

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect("accounts:dashboard")
        else:
            messages.error(request, "Invalid username or password")

    return render(request, "accounts/login.html")


# --- Logout View ---
def logout_view(request):
    logout(request)
    return redirect("accounts:login")


# --- Admin Only User Creation ---
@login_required
@user_passes_test(admin_required)
def create_user_view(request):
    if request.method == "POST":
        username = request.POST.get("username").strip()
        password = request.POST.get("password").strip()

        if User.objects.filter(username=username).exists():
            messages.error(request, "User already exists.")
            return render(request, "accounts/create_user.html")

        User.objects.create_user(
            username=username,
            password=password,
            is_staff=True  # optional: allow admin dashboard login
        )

        messages.success(request, "User created successfully.")
        return redirect("accounts:dashboard")

    return render(request, "accounts/create_user.html")
