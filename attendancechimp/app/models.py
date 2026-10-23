"""
models.py — Data model for AttendanceChimp.

AttendanceChimp is an electronic class attendance tool.  Instructors create
courses and lectures; each lecture is assigned a random QR code.  Students
photograph the QR code and upload the image.  The system decodes the QR code,
matches it to a lecture, and records the attendance.

Entities
--------
- CourseProfile   : extends Django User → instructor-specific data
- StudentProfile  : extends Django User → student-specific data
- Course          : a course taught by one instructor
- Enrollment      : junction table linking students to courses
- Lecture         : a single class meeting (has a QR-code identifier)
- QRCodeUpload    : a student's uploaded QR-code photograph
"""

from django.db import models
from django.contrib.auth.models import User

import logging
import string
import random
import uuid

logger = logging.getLogger(__name__) # set up tracking, auditing, and debugging
                                                               # allows using logger.warning(), logger.error(), 
                                                               # logger.info(), etc. Better than print() for debuggin... 


# ---------------------------------------------------------------------------
# User profiles
# ---------------------------------------------------------------------------
class InstructorProfile(models.Model):
    """Identify a user who can teach courses.

    Each user can have at most one instructor profile.
    Protect the linked account from deletion while this profile exists.
    """

    user = models.OneToOneField(
        User,
        on_delete=models.PROTECT,
        related_name="instructor_profile",
    )

    def __str__(self):
        return self.user.username


class StudentProfile(models.Model):
    """Identify a user who can enroll and submit attendance.

    Each user can have at most one student profile.
    Protect the linked account from deletion while this profile exists.
    """

    user = models.OneToOneField(
        User,
        on_delete=models.PROTECT,
        related_name="student_profile",
    )

    def __str__(self):
        return self.user.username



# ---------------------------------------------------------------------------
# Course
# ---------------------------------------------------------------------------
class Course(models.Model):
    """A course taught by one instructor.

    Meeting days are stored as text, such as 'Mon,Wed'.
    Start and end times apply to each listed day.
    Protect the instructor profile while a course references it.
    """

    name = models.CharField(max_length=200)
    instructor = models.ForeignKey(
        InstructorProfile,
        on_delete=models.PROTECT,
        related_name="courses",
    )
    meeting_days = models.CharField(max_length=100)
    start_time = models.TimeField()
    end_time = models.TimeField()

    def __str__(self):
        return self.name



# ---------------------------------------------------------------------------
# Enrollment
# ---------------------------------------------------------------------------

class Enrollment(models.Model):
    """Link a student to a course without duplicate enrollments.

    Protect the student and course while this enrollment exists.
    """

    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.PROTECT,
        related_name="enrollments",
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.PROTECT,
        related_name="enrollments",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["student", "course"],
                name="unique_student_course",
            ),
        ]

    def __str__(self):
        return f"{self.student} — {self.course}"


# ---------------------------------------------------------------------------
# Lecture
# ---------------------------------------------------------------------------
class Lecture(models.Model):
    """A scheduled class meeting with a unique QR identifier.

    End time must be later than start time.
    Protect the associated course from deletion.
    """

    course = models.ForeignKey(
        Course,
        on_delete=models.PROTECT,
        related_name="lectures",
    )
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    qr_identifier = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(ends_at__gt=models.F("starts_at")),
                name="lecture_end_after_start",
            ),
        ]

    def __str__(self):
        return f"{self.course} — {self.starts_at}"



# ---------------------------------------------------------------------------
# QR Code Upload
# ---------------------------------------------------------------------------
class QRCodeUpload(models.Model):
    """A student's uploaded attendance image.

    The lecture may be unknown until the image is processed.
    Once identified, only one upload per student per lecture is allowed.
    Protect the referenced student and lecture from deletion.
    """

    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.PROTECT,
        related_name="qr_uploads",
    )
    lecture = models.ForeignKey(
        Lecture,
        on_delete=models.PROTECT,
        related_name="qr_uploads",
        null=True,
        blank=True,
    )
    image = models.FileField(upload_to="qr_uploads/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["student", "lecture"],
                name="unique_student_lecture_upload",
            ),
        ]

    def __str__(self):
        return f"Upload {self.pk} by {self.student}"



# ---------------------------------------------------------------------------
# Helper / API functions
# ---------------------------------------------------------------------------



