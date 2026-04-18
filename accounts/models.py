from django.db import models
from django.contrib.auth.models import AbstractUser

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
