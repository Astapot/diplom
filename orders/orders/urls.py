"""
URL configuration for orders project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include

from backend.views import (PartnerUpdate, MyUserRegistration, UserLogin, ProductsView, ProductDetailView, BasketView,
                           ContactView, NewOrdersView, )

from rest_framework.routers import DefaultRouter


#
#
# router = DefaultRouter()
# router.register('user', MyUserViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    # path('api/', include(router.urls)),
    path('partner/update', PartnerUpdate.as_view()),
    path('registration/', MyUserRegistration.as_view()),
    path('login/', UserLogin.as_view()),
    path('products/', ProductsView.as_view()),
    path('products/<int:id>/', ProductDetailView.as_view()),
    path('basket/', BasketView.as_view()),
    path('contacts/', ContactView.as_view()),
    path('neworders/', NewOrdersView.as_view())
]
