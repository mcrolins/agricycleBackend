from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.
class User(AbstractUser):
    class Role(models.TextChoices):
        FARMER = 'FARMER', 'Farmer'
        PROCESSOR = 'PROCESSOR', 'Processor'
    role = models.CharField(max_length=20, choices=Role.choices)
    
    phone_number = models.CharField(max_length=20, unique=True)
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()