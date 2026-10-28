"""
views.py — HTTP request handlers for AttendanceChimp.

Each view corresponds to one URL endpoint.  Views receive an HTTP request,
interact with the database via models.py, and return an HTTP response.
"""

from django.shortcuts import render, redirect
from django.http import (HttpResponse, HttpResponseForbidden,
                         HttpResponseBadRequest, JsonResponse)
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from django.db import IntegrityError, transaction
from .models import StudentProfile, InstructorProfile
from datetime import datetime
import zoneinfo
import json
import io

# from .models import (InstructorProfile, StudentProfile, Course, Enrollment,
#                      Lecture, QRCodeUpload, is_instructor, is_student,
#                      getUploadsForCourse)

CDT = zoneinfo.ZoneInfo("America/Chicago")


# ---------------------------------------------------------------------------
# HW2  — index, time, sum
# ---------------------------------------------------------------------------

def index(request):
    """Display the home page with Central time and user information."""

    context = {
        "current_time": datetime.now(CDT).strftime("%H:%M"),
        "current_user": request.user,
    }
    return render(request, "app/index.html", context)

def time_view(request):
    current_time = datetime.now(CDT).strftime("%H:%M")
    return HttpResponse(current_time, content_type="text/plain")


def sum_view(request):
    try:
        n1 = float(request.GET["n1"])
        n2 = float(request.GET["n2"])
    except (KeyError, ValueError):
        return HttpResponseBadRequest("Provide numbers for n1 and n2.")

    return HttpResponse(f"<p>{n1 + n2:g}</p>")

# ---------------------------------------------------------------------------
# HW4  — user creation
# ---------------------------------------------------------------------------
def new(request):
    """Display the sign-up form for GET requests only."""

    if request.method != "GET":
        return HttpResponse(
            "Method not allowed.",
            status=405,
            headers={"Allow": "GET"},
        )

    return render(request, "app/new.html")

@csrf_exempt
def createUser(request):
    """Create an account and profile, then sign the user in."""

    if request.method != "POST":
        return HttpResponse(
            "Method not allowed.",
            status=405,
            headers={"Allow": "POST"},
        )

    username = request.POST.get("user_name", "").strip()
    email = request.POST.get("email", "").strip()
    password = request.POST.get("password", "")
    is_student = request.POST.get("is_student", "")

    if not username or not email or not password:
        return HttpResponseBadRequest("All fields are required.")

    if is_student not in ("0", "1"):
        return HttpResponseBadRequest("Choose student or instructor.")

    if User.objects.filter(email__iexact=email).exists():
        return HttpResponseBadRequest("This email is already registered.")

    if User.objects.filter(username=username).exists():
        return HttpResponseBadRequest("This username is already taken.")

    try:
        with transaction.atomic():
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
            )

            if is_student == "1":
                StudentProfile.objects.create(user=user)
            else:
                InstructorProfile.objects.create(user=user)

    except IntegrityError:
        return HttpResponseBadRequest("Unable to create this account.")

    login(request, user)
    return HttpResponse("Account created successfully.", status=200)

# ---------------------------------------------------------------------------
# HW5  — courses, lectures, QR uploads, dump
# ---------------------------------------------------------------------------



# ---------------------------------------------------------------------------
# HW6  — getUploads
# ---------------------------------------------------------------------------



