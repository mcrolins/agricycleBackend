from django.urls import path

from .views import AdminReportsView, FarmerReportsView, ProcessorReportsView, admin_dashboard


urlpatterns = [
    path("farmer/", FarmerReportsView.as_view(), name="farmer_reports"),
    path("processor/", ProcessorReportsView.as_view(), name="processor_reports"),
    path("admin/", AdminReportsView.as_view(), name="admin_reports"),
    path("admin/dashboard/", admin_dashboard, name="admin_dashboard"),
]
