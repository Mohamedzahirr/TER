from django.utils import timezone
from django.contrib.auth.models import AbstractUser
from django.db import models
import random
import string
from django.conf import settings


class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('employee', 'Employee'),
        ('team_lead', 'Team Lead'),
    )

    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='manager')
    is_active = models.BooleanField(default=True)
    pointage_code = models.CharField(max_length=4, unique=True, blank=True, null=True)
    created_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='employees')
    hours_per_week = models.IntegerField(default=0)
    photo = models.ImageField(upload_to='photos/', null=True, blank=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    def generate_unique_pointage_code(self):
        while True:
            code = ''.join(random.choices(string.digits, k=4))
            if not CustomUser.objects.filter(pointage_code=code).exists():
                return code

    def save(self, *args, **kwargs):
        if not self.pointage_code:
            self.pointage_code = self.generate_unique_pointage_code()
        super().save(*args, **kwargs)

class Availability(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='availabilities')
    day_of_week = models.CharField(max_length=10)
    start_time = models.TimeField()
    end_time = models.TimeField()

    def __str__(self):
        return f"{self.user.username} - {self.day_of_week} {self.start_time} to {self.end_time}"
    
    
class ServiceConstraints(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    monday_start = models.TimeField()
    monday_end = models.TimeField()
    tuesday_start = models.TimeField()
    tuesday_end = models.TimeField()
    wednesday_start = models.TimeField()
    wednesday_end = models.TimeField()
    thursday_start = models.TimeField()
    thursday_end = models.TimeField()
    friday_start = models.TimeField()
    friday_end = models.TimeField()
    saturday_start = models.TimeField()
    saturday_end = models.TimeField()
    sunday_start = models.TimeField()
    sunday_end = models.TimeField()
    max_work_hours_per_day = models.IntegerField()
    max_consecutive_work_hours = models.IntegerField()
    min_break_minutes = models.IntegerField()
    max_work_hours_per_week = models.IntegerField(default=40)
    min_consecutive_rest_days = models.IntegerField(default=2)  # Nouveau champ
    
    def __str__(self):
        return f'Contraintes de {self.user.username}'
    
class EmployeeRequirement(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    day_of_week = models.CharField(max_length=10, choices=[
        ('Monday', 'Lundi'),
        ('Tuesday', 'Mardi'),
        ('Wednesday', 'Mercredi'),
        ('Thursday', 'Jeudi'),
        ('Friday', 'Vendredi'),
        ('Saturday', 'Samedi'),
        ('Sunday', 'Dimanche')
    ])

class Shift(models.Model):
    employee_requirement = models.ForeignKey(EmployeeRequirement, related_name='shifts', on_delete=models.CASCADE)
    start_time = models.TimeField()
    end_time = models.TimeField()
    employees_required = models.IntegerField()

    def __str__(self):
        return f"{self.start_time} - {self.end_time} : {self.employees_required} employés"

class ShiftRequirement(models.Model):
    constraint = models.ForeignKey(ServiceConstraints, on_delete=models.CASCADE, related_name='shift_requirements')
    day_of_week = models.CharField(max_length=10, choices=[
        ('Monday', 'Lundi'),
        ('Tuesday', 'Mardi'),
        ('Wednesday', 'Mercredi'),
        ('Thursday', 'Jeudi'),
        ('Friday', 'Vendredi'),
        ('Saturday', 'Samedi'),
        ('Sunday', 'Dimanche'),
    ])
    start_time = models.TimeField()
    end_time = models.TimeField()
    required_employees = models.PositiveIntegerField()
    def __str__(self):
        return f"{self.day_of_week} {self.start_time} - {self.end_time} : {self.employees_required} employés"
    


class Schedule(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    

    class Meta:
        unique_together = ('user', 'start_date', 'end_date')

class ScheduleEntry(models.Model):
    schedule = models.ForeignKey(Schedule, related_name='entries', on_delete=models.CASCADE)
    employee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    day = models.CharField(max_length=10)
    start_time = models.TimeField()
    end_time = models.TimeField()
    hours = models.IntegerField()


class LeaveRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('approved', 'Approuvée'),
        ('rejected', 'Rejetée')
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    submitted_at = models.DateTimeField(default=timezone.now)
    comments = models.TextField(blank=True, null=True)
    alternative_start_date = models.DateField(blank=True, null=True)
    alternative_end_date = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"Demande de {self.user.username} du {self.start_date} au {self.end_date}"


    
class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)  # New field to track if notification is read
    notification_type = models.CharField(max_length=50)  # Ajoutez cette ligne si elle manque
    redirect_url = models.URLField(max_length=200, blank=True, null=True)  # Ajoutez cette ligne

    class Meta:
        ordering = ['-created_at']




class TimeClock(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    clock_in_time = models.DateTimeField(null=True, blank=True)
    clock_out_time = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f'{self.user.username} - {self.clock_in_time} to {self.clock_out_time}'
