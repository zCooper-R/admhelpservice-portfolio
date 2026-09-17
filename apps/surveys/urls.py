from django.urls import path

from apps.surveys import views

app_name = "surveys"

urlpatterns = [
    path("api/current-popup/", views.CurrentSurveyPopupView.as_view(), name="current_popup"),
    path("api/submit/", views.SubmitSurveyPopupView.as_view(), name="submit_popup"),
]
