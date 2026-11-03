from django.urls import path

from .views import FacilityListView, HealthView

urlpatterns = [
    path("facilities", FacilityListView.as_view(), name="facility-list"),
    path("health", HealthView.as_view(), name="health"),
]
