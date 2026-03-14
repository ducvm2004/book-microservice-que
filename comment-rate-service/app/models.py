from django.db import models


class Rating(models.Model):
    customer_id = models.IntegerField()
    book_id = models.IntegerField()
    rating = models.IntegerField()
    comment = models.TextField()
