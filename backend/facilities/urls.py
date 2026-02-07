from django.urls import path

from .views import FacilityListView

urlpatterns = [
    path("facilities", FacilityListView.as_view(), name="facility-list"),
]

