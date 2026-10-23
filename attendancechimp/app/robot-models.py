# AttendanceChimp with InstructorProfile, StudentProfile, Course, Enrollment, Lecture, and QRCodeUpload. Use Django's built-in User.
import uuid

from django.contrib.auth.models import User
from django.db import models


class InstructorProfile(models.Model):
    """An instructor linked to a Django user account."""

    user = models.OneToOneField(User, on_delete=models.CASCADE)


class StudentProfile(models.Model):
    """A student linked to a Django user account."""

    user = models.OneToOneField(User, on_delete=models.CASCADE)


class Course(models.Model):
    """A course with an instructor and a readable schedule."""

    name = models.CharField(max_length=200)
    instructor = models.ForeignKey(
        InstructorProfile,
        on_delete=models.CASCADE,
    )
    meeting_schedule = models.CharField(max_length=200)


class Enrollment(models.Model):
    """One student's enrollment in one course."""

    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
    )
    course = models.ForeignKey(Course, on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["student", "course"],
                name="robot_unique_enrollment",
            ),
        ]


class Lecture(models.Model):
    """A course meeting identified by a unique QR value."""

    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    date = models.DateField()
    qr_identifier = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )


class QRCodeUpload(models.Model):
    """An uploaded file linked to a student and known lecture."""

    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
    )
    lecture = models.ForeignKey(
        Lecture,
        on_delete=models.CASCADE,
    )
    image = models.FileField(upload_to="qr_uploads/")
    uploaded_at = models.DateTimeField(auto_now_add=True)
