from django.db import models


class Shipment(models.Model):
    order_id = models.IntegerField()
    status = models.CharField(max_length=50)
