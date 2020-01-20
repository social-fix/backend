import requests
from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import EmailMessage
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_text
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import permissions, status, viewsets
from rest_framework.authentication import (SessionAuthentication,
                                           TokenAuthentication)
from rest_framework.authtoken import views as rest_framework_views
from rest_framework.decorators import action
from rest_framework.response import Response
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import *
from .permissions import (IsAuthenticatedOrCreate, IsOwnerOrReadOnly,
                          IsSenderOrReadOnly)
from .serializers import *
from .tokens import account_activation_token

import os


class CsrfExemptSessionAuthentication(SessionAuthentication):

    def enforce_csrf(self, request):
        return  # To not perform the csrf check previously happening


class UserView(viewsets.ModelViewSet):
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    permission_classes = [permissions.AllowAny]
    #permission_classes = [IsOwnerOrReadOnly, IsAuthenticatedOrCreate]
    authentication_classes = [TokenAuthentication]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save(is_active=False)
        mail_subject = "activate your account on socialfix"
        current_site = get_current_site(request)
        message = render_to_string('confirmation_email.html', {
            'name': user.name,
            'domain': current_site.domain,
            'uid': ((user.pk)),
            'token': account_activation_token.make_token(user),
        })
        email_to = user.email
        email = EmailMessage(
            mail_subject, message, to=[email_to]
        )
        email.send()
        headers = self.get_success_headers(serializer.data)
        return Response("yo", status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        if ("location" in request.data):
            location = request.data["location"]
            url = 'https://maps.googleapis.com/maps/api/geocode/json'
            params = {'address': '{} {} {} {}'.format(location['street'], location['house_number'], location['postal_code'], location['city']).replace(' ', '+'),
                      'components': 'country:{}'.format(location['country']),
                      'key': settings.GOOGLE_API_KEY
                      }
            result = requests.get(url, params=params).json()
            if (len(result['results']) > 0):
                location['coordinates'] = {'x': None, 'y': None}
                location['coordinates']['x'] = result['results'][0]['geometry']['location']['lat']
                location['coordinates']['y'] = result['results'][0]['geometry']['location']['lng']
                request.data["location"] = location
            else:
                return HttpResponseBadRequest('The location could not be determined based on the given address')
        return super().update(request, *args, **kwargs)


class ServiceView(viewsets.ModelViewSet):
    #permission_classes = [IsSenderOrReadOnly, IsAuthenticatedOrCreate]
    permission_classes = [permissions.AllowAny]
    authentication_classes = [TokenAuthentication]
    model_class = Service
    queryset = model_class.objects.all().select_subclasses()
    serializer_class = ServiceSerializer

    # Well, this is very ugly but as far as I know, there is no polymorphic serializer...
    def getSerializedData(self, model):
        serializer = None
        className = model.__class__.__name__
        if (className == 'Bed'):
            serializer = BedSerializer
        elif (className == 'Meal'):
            serializer = MealSerializer
        elif (className == 'Washing'):
            serializer = WashingSerializer
        else:
            serializer = ServiceSerializer
        return dict(serializer(model).data, type=className.lower())

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializedData = [self.getSerializedData(
            service) for service in queryset]
        return Response(serializedData)

    @action(methods=['get'], detail=False,
            url_path='groupedList')
    def groupedList(self, request):
        queryset = self.get_queryset()
        serializedData = [self.getSerializedData(
            service) for service in queryset]
        group_by_sender = {}
        for sender in queryset.values_list('sender', flat=True).distinct():
            group_by_sender[sender] = [service for service in serializedData if service['sender']['id']==sender]
            print(group_by_sender)
        return Response(group_by_sender)
        
    @action(methods=['get'], detail=False,
            url_path='getBySender/(?P<sender_id>[0-9]+)')
    def getBySender(self, request, sender_id):
        filteredSet = self.queryset.filter(sender=sender_id)
        serializedData = [self.getSerializedData(
            service) for service in filteredSet]
        return Response(serializedData)

    @action(methods=['get'], detail=False, permission_classes=[permissions.IsAuthenticated],
            url_path='getIfIsGuest/(?P<guest_id>[0-9]+)')
    def getIfIsGuest(self, request, guest_id):
        filteredSet = self.queryset.filter(guests=guest_id).distinct()
        serializedData = [self.getSerializedData(
            service) for service in filteredSet]
        return Response(serializedData)

    @action(methods=['post'], detail=False, permission_classes=[permissions.IsAuthenticated],
            url_path='subscribeToHelp/(?P<help_id>[0-9]+)')
    def subscribeToHelp(self, request, help_id):
        user = Profile.objects.get(pk=request.user.id)
        if user:
            instance = self.model_class.objects.get(pk=help_id)
            instance.guests.add(user)
            instance.save()
            async_to_sync(get_channel_layer().group_send)(
                'service_{}'.format(instance.id),
                {
                    "type": "subscription_message",
                    "message": self.getSerializedData(instance),
                },
            )
            return Response("user {} subscribed to help n°{}".format(user, instance.id))
        else:
            return HttpResponseBadRequest


class MealView(ServiceView):
    model_class = Meal
    serializer_class = MealSerializer


class WashingView(ServiceView):
    model_class = Washing
    serializer_class = WashingSerializer


class BedView(ServiceView):
    model_class = Bed
    serializer_class = BedSerializer


class ObtainAuthTokenWithEmail(rest_framework_views.ObtainAuthToken):
    serializer_class = AuthTokenSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data,
                                           context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user': ProfileSerializer(user).data
        })


def activate(request, uidb64, token):
    try:
        uid = ((uidb64))
        user = Profile.objects.get(pk=uid)
        token_check = account_activation_token.check_token(user, token)
    except(TypeError, ValueError, OverflowError, Profile.DoesNotExist):
        user = None
    if user is not None and token_check:
        user.is_active = True
        user.save()
        #login(request, user)
        return redirect('http://localhost:4200/finalizedRegistration')
    else:
        return HttpResponse("Activation link is invalid! {} {}, {}".format(user, token_check, uid))


obtain_auth_token = ObtainAuthTokenWithEmail.as_view()
