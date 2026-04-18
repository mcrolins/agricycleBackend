from django.urls import path

from .views import (
    AdminReportsView, 
    FarmerReportsView, 
    ProcessorReportsView, 
    admin_dashboard, 
    AdminUsersCSV, 
    AdminListingsCSV, 
    AdminOrdersCSV
)


urlpatterns = [
    path("farmer/", FarmerReportsView.as_view(), name="farmer_reports"),
    path("processor/", ProcessorReportsView.as_view(), name="processor_reports"),
    path("admin/", AdminReportsView.as_view(), name="admin_reports"),
    path("admin/dashboard/", admin_dashboard, name="admin_dashboard"),
    path("admin/users.csv/", AdminUsersCSV.as_view(), name="admin_users_csv"),
    path("admin/listings.csv/", AdminListingsCSV.as_view(), name="admin_listings_csv"),
    path("admin/orders.csv/", AdminOrdersCSV.as_view(), name="admin_orders_csv"),
]
