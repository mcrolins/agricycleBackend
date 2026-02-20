from django.db import models
from django.conf import settings
from django.db import models
from listings.models import WasteListing


class WasteRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        ACCEPTED = "ACCEPTED", "Accepted"
        REJECTED = "REJECTED", "Rejected"
        CANCELLED = "CANCELLED", "Cancelled"
        COMPLETED = "COMPLETED", "Completed"

    listing = models.ForeignKey(WasteListing, on_delete=models.CASCADE, related_name="requests")
    processor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="waste_requests")

    quantity_requested = models.DecimalField(max_digits=12, decimal_places=2)
    proposed_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            # Prevent same processor from spamming same listing multiple times
            models.UniqueConstraint(fields=["listing", "processor"], name="unique_request_per_listing_per_processor")
        ]

    def __str__(self):
        return f"Request {self.id} -> Listing {self.listing_id} ({self.status})"


class RequestMessage(models.Model):
    request = models.ForeignKey(WasteRequest, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_request_messages")
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Msg {self.id} (Req {self.request_id})"

