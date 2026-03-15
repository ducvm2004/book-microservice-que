from django.db import models


class Order(models.Model):
    customer_id = models.IntegerField()
    status = models.CharField(max_length=50, default='PENDING')
    # ADDED-ASSIGNMENT06: track saga steps and compensation reason.
    payment_reserved = models.BooleanField(default=False)
    shipping_reserved = models.BooleanField(default=False)
    compensation_reason = models.CharField(max_length=255, blank=True, default='')
