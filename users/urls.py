from django.urls import path, include, re_path
from . import views
from rest_framework import routers


router = routers.DefaultRouter()
router.register('users', views.UserView)
router.register('service/meal', views.MealView)
router.register('service/bed', views.BedView)
router.register('service/washing', views.WashingView)
router.register('service', views.ServiceView)
urlpatterns = [
    path('', include(router.urls)),
    re_path(r'^users/activate/(?P<uidb64>[0-9A-Za-z_\-\']+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        views.activate, name='activate'),
    path('get_auth_token/', views.obtain_auth_token, name='get_auth_token'),
]