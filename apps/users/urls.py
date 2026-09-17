from django.contrib.auth.views import LogoutView
from django.urls import path

from apps.users.views import myLoginView, myLogoutView

app_name = 'auth'

urlpatterns = [
    path('login/', myLoginView.as_view(), name='login'),
    path('logout/', myLogoutView.as_view(), name='logout'),
]
