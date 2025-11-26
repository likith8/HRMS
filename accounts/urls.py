from django.urls import path
from . import views

app_name = "accounts"   # <- MUST BE HERE

urlpatterns = [
    path("", views.home, name="home"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("create-user/", views.create_user_view, name="create_user"),
]