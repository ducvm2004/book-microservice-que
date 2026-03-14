from django.db import models


class Staff(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
