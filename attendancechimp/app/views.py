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
from .models import StudentProfile, InstructorProfile, Course
from datetime import datetime
from .models import getUploadsForCourse

import zoneinfo
import json
import io
from .models import StudentProfile, InstructorProfile, Course, Lecture
from .models import (
    StudentProfile, InstructorProfile, Course, Lecture, QRCodeUpload,
)
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
def new_course(request):
    """Show the course form to logged-in instructors."""

    if not request.user.is_authenticated:
        return HttpResponse("Instructor access required.", status=401)

    if not InstructorProfile.objects.filter(user=request.user).exists():
        return HttpResponse("Instructor access required.", status=401)

    if request.method != "GET":
        return HttpResponse(
            "Method not allowed.", status=405,
            headers={"Allow": "GET"},
        )

    return render(request, "app/new_course.html")


@csrf_exempt
def createCourse(request):
    """Create a course belonging to the logged-in instructor."""

    if not request.user.is_authenticated:
        return HttpResponse("Instructor access required.", status=401)

    instructor = InstructorProfile.objects.filter(
        user=request.user
    ).first()

    if instructor is None:
        return HttpResponse("Instructor access required.", status=401)

    if request.method != "POST":
        return HttpResponse(
            "Method not allowed.", status=405,
            headers={"Allow": "POST"},
        )

    name = request.POST.get("course-name", "").strip()
    course_number = request.POST.get("course-number", "").strip()

    if not course_number or len(course_number) > 50:
        return HttpResponseBadRequest(
            "Provide a course number of at most 50 characters."
        )
    start_text = request.POST.get("start-time", "")
    end_text = request.POST.get("end-time", "")

    days = [
        day for day in ("mon", "tue", "wed", "thu", "fri")
        if f"day-{day}" in request.POST
    ]

    if not name or len(name) > 200 or not days:
        return HttpResponseBadRequest(
            "Provide a course name and at least one meeting day."
        )

    try:
        start = datetime.strptime(start_text, "%H:%M").time()
        end = datetime.strptime(end_text, "%H:%M").time()
    except ValueError:
        return HttpResponseBadRequest("Use HH:MM for meeting times.")

    if end <= start:
        return HttpResponseBadRequest(
            "End time must be later than start time."
        )

    try:
        with transaction.atomic():
            Course.objects.create(
                name=name,
                instructor=instructor,
                meeting_days=",".join(days),
                start_time=start,
                end_time=end,
                mon="mon" in days,
                tue="tue" in days,
                wed="wed" in days,
                thu="thu" in days,
                fri="fri" in days,
            )
    except IntegrityError:
        return HttpResponseBadRequest(
            "That course name or course number already exists."
        )

    return HttpResponse("Course created successfully.", status=200)
def new_lecture(request):
    """Show available courses to a logged-in instructor."""

    if not request.user.is_authenticated:
        return HttpResponse("Instructor access required.", status=401)

    if not InstructorProfile.objects.filter(user=request.user).exists():
        return HttpResponse("Instructor access required.", status=401)

    if request.method != "GET":
        return HttpResponse(
            "Method not allowed.", status=405,
            headers={"Allow": "GET"},
        )

    return render(
        request,
        "app/new_lecture.html",
        {"courses": Course.objects.order_by("name")},
    )


@csrf_exempt
def createLecture(request):
    """Create a lecture for the selected course."""

    if not request.user.is_authenticated:
        return HttpResponse("Instructor access required.", status=401)

    if not InstructorProfile.objects.filter(user=request.user).exists():
        return HttpResponse("Instructor access required.", status=401)

    if request.method != "POST":
        return HttpResponse(
            "Method not allowed.", status=405,
            headers={"Allow": "POST"},
        )

    course_name = request.POST.get("choice", "").strip()
    course = Course.objects.filter(name=course_name).first()

    if course is None:
        return HttpResponseBadRequest("Select an existing course.")

    today = datetime.now(CDT).date()
    starts_at = datetime.combine(today, course.start_time, tzinfo=CDT)
    ends_at = datetime.combine(today, course.end_time, tzinfo=CDT)

    if ends_at <= starts_at:
        return HttpResponseBadRequest("The course has invalid meeting times.")

    Lecture.objects.create(
        course=course,
        starts_at=starts_at,
        ends_at=ends_at,
    )

    return HttpResponse("Lecture created successfully.", status=200)

def new_qr_upload(request):
    """Show the upload form to a logged-in student."""

    if not request.user.is_authenticated:
        return HttpResponse("Student access required.", status=401)

    if not StudentProfile.objects.filter(user=request.user).exists():
        return HttpResponse("Student access required.", status=401)

    if request.method != "GET":
        return HttpResponse(
            "Method not allowed.", status=405,
            headers={"Allow": "GET"},
        )

    return render(request, "app/new_qr_upload.html")


@csrf_exempt
def createQRCodeUpload(request):
    """Save an uploaded file for the logged-in student."""

    if not request.user.is_authenticated:
        return HttpResponse("Student access required.", status=401)

    student = StudentProfile.objects.filter(user=request.user).first()

    if student is None:
        return HttpResponse("Student access required.", status=401)

    if request.method != "POST":
        return HttpResponse(
            "Method not allowed.", status=405,
            headers={"Allow": "POST"},
        )

    image = request.FILES.get("imageUpload")

    if image is None:
        return HttpResponseBadRequest("Select an image to upload.")

    QRCodeUpload.objects.create(
        student=student,
        image=image,
    )

    return HttpResponse("Upload saved successfully.", status=200)

def dumpUploads(request):
    """Return upload usernames and timestamps to instructors."""

    if not request.user.is_authenticated:
        return HttpResponse("Instructor access required.", status=401)

    if not InstructorProfile.objects.filter(user=request.user).exists():
        return HttpResponse("Instructor access required.", status=401)

    if request.method != "GET":
        return HttpResponse(
            "Method not allowed.", status=405,
            headers={"Allow": "GET"},
        )

    uploads = QRCodeUpload.objects.select_related(
        "student__user"
    ).order_by("uploaded_at", "id")

    data = [
        {
            "username": upload.student.user.username,
            "upload_time": upload.uploaded_at.astimezone(CDT).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
        }
        for upload in uploads
    ]

    return JsonResponse(data, safe=False)

# ---------------------------------------------------------------------------
# HW6  — getUploads
# ---------------------------------------------------------------------------

def getUploads(request):
    """Return time-valid uploads for a course to instructors."""

    if not request.user.is_authenticated:
        return HttpResponse("Instructor access required.", status=401)

    if not InstructorProfile.objects.filter(user=request.user).exists():
        return HttpResponse("Instructor access required.", status=401)

    if request.method != "GET":
        return HttpResponse(
            "Method not allowed.",
            status=405,
            headers={"Allow": "GET"},
        )

    course_number = request.GET.get("course", "").strip()

    if not course_number:
        return JsonResponse(
            {"error": "Missing course parameter"},
            status=400,
        )

    uploads = getUploadsForCourse(course_number)

    data = [
        {
            "username": upload.student.user.username,
            "upload_time": upload.uploaded_at.astimezone(CDT).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
        }
        for upload in uploads
    ]

    return JsonResponse(data, safe=False)

