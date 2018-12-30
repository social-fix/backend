from django.db import models
from django.contrib.auth.models import PermissionsMixin
from django.contrib.auth.base_user import AbstractBaseUser
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from rest_framework.authtoken.models import Token
from .managers import ProfileManager
from django.contrib.auth.models import UserManager
from model_utils.managers import InheritanceManager

class GeoPoint(models.Model):
    x = models.DecimalField(max_digits=16, decimal_places=14)
    y = models.DecimalField(max_digits=16, decimal_places=14)

class Location(models.Model):
    street = models.TextField(max_length=200, blank=True, null=True)
    house_number = models.PositiveIntegerField(blank=True, null=True)
    postal_code = models.PositiveIntegerField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    coordinates = models.OneToOneField(GeoPoint, on_delete=models.CASCADE)

class Profile(AbstractBaseUser):
    name = models.CharField(max_length=100)
    email = models.EmailField(verbose_name='email address', unique=True)
    is_active = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    birthdate = models.DateTimeField()
    gender = models.PositiveIntegerField()
    catchPhrase = models.TextField(max_length=200, default="", blank=True, null=True)
    description = models.TextField(max_length=500, default="", blank=True, null=True)
    location = models.OneToOneField(Location, on_delete=models.CASCADE, default=None, null=True, blank=True)

    objects = ProfileManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = [name,email]

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')

    def get_full_name(self):
        return self.name

    def get_short_name(self):
        return self.name


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created:
        Token.objects.create(user=instance)
    
class Service(models.Model):
    sender = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='%(class)s_sender')
    guests = models.ManyToManyField(Profile, default=None, blank=True)
    start = models.DateTimeField()
    end = models.DateTimeField()
    comment = models.TextField(max_length=500, default="", blank=True, null=True)
    guest_limit = models.PositiveIntegerField(default=1)
    objects = InheritanceManager()

class Meal(Service):
    can_be_casher = models.BooleanField(default=True)
    can_be_halal = models.BooleanField(default=True)
    can_be_vegetarian = models.BooleanField(default=True)
    can_be_vegan = models.BooleanField(default=True)

    
class Washing(Service):
    toilet_available = models.BooleanField(default=True)
    shower_available = models.BooleanField(default=True)
    bath_available = models.BooleanField(default=True)
    laundry_available = models.BooleanField(default=True)

class Bed(Service):
    number_nights = models.PositiveIntegerField()
