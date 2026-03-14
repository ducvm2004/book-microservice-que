from django.db import models


class Manager(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
