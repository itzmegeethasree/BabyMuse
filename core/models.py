from django.db import models


class Banner(models.Model):
    title = models.CharField(max_length=200)
    image = models.ImageField(upload_to='banners/')
    link = models.URLField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    age_min = models.PositiveBigIntegerField(null=True, blank=True)
    age_max = models.PositiveBigIntegerField(null=True, blank=True)
    gender = models.CharField(max_length=10,
                              choices=[('Male', 'Male'),
                                       ('Female', 'Female'),
                                       ('Unisex', 'Unisex')],
                              default='Unisex')

    def is_suitable_for(self, baby):
        age = baby.age_in_months()
        if age is None:
            return False
        return (
            (self.age_min is None or age >= self.age_min) and
            (self.age_max is None or age <= self.age_max) and
            (self.gender == 'Unisex' or self.gender == baby.baby_gender)
        )

    def __str__(self):
        return self.title


class FAQ(models.Model):
    question = models.CharField(max_length=255)
    answer = models.TextField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.question


class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.email}"
