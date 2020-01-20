from rest_framework import serializers
from django.contrib.auth import authenticate
from django.utils.translation import ugettext_lazy as _
from . models import *
from . fields import AsymetricRelatedField
from drf_writable_nested import WritableNestedModelSerializer

class GeoPointSerializer(serializers.ModelSerializer):
    x = serializers.DecimalField(max_digits=16, decimal_places=14)
    y = serializers.DecimalField(max_digits=16, decimal_places=14)
    class Meta:
        fields = ('x', 'y')
        model = GeoPoint

class LocationSerializer(WritableNestedModelSerializer):
    street = serializers.CharField(max_length=200)
    house_number = serializers.IntegerField()
    postal_code = serializers.IntegerField()
    city = serializers.CharField(max_length=100)
    coordinates = GeoPointSerializer()
    class Meta:
        fields = ('street', 'house_number', 'postal_code', 'city', 'country', 'coordinates')
        model = Location

    def create(self, validated_data):
        relations, reverse_relations = self._extract_relations(validated_data)
        # Create or update direct relations (foreign key, one-to-one)
        self.update_or_create_direct_relations(
            validated_data,
            relations,
        )
        location = Location.objects.create(**validated_data)
        self.update_or_create_reverse_relations(location, reverse_relations)
        return location


class ProfileSerializer(WritableNestedModelSerializer):
    location = LocationSerializer(required=False)
    class Meta:
        model = Profile
        fields = ('objects','id', 'name', 'email', 'password', 'is_active', 'birthdate', 'gender', 'catchPhrase', 'description', 'location')

    def create(self, validated_data):
        relations, reverse_relations = self._extract_relations(validated_data)
        # Create or update direct relations (foreign key, one-to-one)
        self.update_or_create_direct_relations(
            validated_data,
            relations,
        )
        user = Profile.objects.create_user(**validated_data)
        self.update_or_create_reverse_relations(user, reverse_relations)
        return user

class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = '__all__'
    sender = AsymetricRelatedField.from_serializer(ProfileSerializer)

class MealSerializer(ServiceSerializer):
    class Meta:
        model = Meal
        fields = '__all__'

class WashingSerializer(ServiceSerializer):

    class Meta:
        model = Washing
        fields = '__all__'

class BedSerializer(ServiceSerializer):

    class Meta:
        model = Bed
        fields = '__all__'
        
class AuthTokenSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(style={'input_type': 'password'})

    def validate(self, data):
        email = data.get('email')
        password = data.get('password')

        if email and password:
            user = authenticate(email=email, password=password)
            # if user:
            #     if not user.is_active:
            #         msg = _('User account is disabled.')
            #         raise serializers.ValidationError(msg)
            if not user:
                msg = _('Unable to log in with provided credentials!')
                raise serializers.ValidationError(msg)
        else:
            msg = _('Must include "email" and "password".')
            raise serializers.ValidationError(msg)
        data['user'] = user
        return data