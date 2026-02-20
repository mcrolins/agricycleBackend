from django.db import models
from django.conf import settings

class WasteListing(models.Model):
    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        REQUESTED = "REQUESTED", "Requested"
        ACCEPTED = "ACCEPTED", "Accepted"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    farmer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="waste_listings")

    waste_type = models.CharField(max_length=120)
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    unit = models.CharField(max_length=30, default="kg")  # kg, bags, tons etc.
    location = models.CharField(max_length=150)

    price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)  # optional
    notes = models.TextField(blank=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.waste_type} - {self.quantity}{self.unit} ({self.status})"

class ListingImage(models.Model):
    listing = models.ForeignKey(WasteListing, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="listing_images/")
    is_primary = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_primary", "-uploaded_at"]

    def __str__(self):
        return f"Image for listing #{self.listing_id}"