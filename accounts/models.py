from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator

class Review(models.Model):
    reviewer = models.ForeignKey('User', on_delete=models.CASCADE, related_name='reviews_given')
    reviewee = models.ForeignKey('User', on_delete=models.CASCADE, related_name='reviews_received')
    request_id = models.IntegerField(null=True, blank=True)
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], null=True, blank=True)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Complaint(models.Model):
    reporter = models.ForeignKey('User', on_delete=models.CASCADE, related_name='complaints_filed')
    reported = models.ForeignKey('User', on_delete=models.CASCADE, related_name='complaints_received')
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Admin'
        FARMER = 'FARMER', 'Farmer'
        PROCESSOR = 'PROCESSOR', 'Processor'
    role = models.CharField(max_length=20, choices=Role.choices)
    
    phone_number = models.CharField(max_length=20, unique=True)
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def is_platform_admin(self):
        return self.role == 'ADMIN' or self.is_superuser
