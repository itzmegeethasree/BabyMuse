from django.db import models

# Create your models here.


class Coupon(models.Model):
    code = models.CharField(max_length=20, unique=True)
    discount = models.DecimalField(
        max_digits=6, decimal_places=2)  # as amount or percentage
    is_percentage = models.BooleanField(default=False)
    active = models.BooleanField(default=True)
    minimum_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()

    def __str__(self):
        return self.code
