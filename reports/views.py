from collections import defaultdict
from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate, TruncMonth
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponseForbidden
from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.views import APIView

from listings.models import WasteListing
from orders.models import WasteRequest

from django.http import HttpResponse
from django.db.models import Q
from accounts.models import User
from listings.models import WasteListing
from orders.models import WasteRequest
from .permissions import IsFarmer, IsPlatformAdmin, IsProcessor

class IsPlatformAdminMixin:
    def has_permission(self, request, view):
        return IsPlatformAdmin().has_permission(request, view)


SALE_STATUSES = [WasteRequest.Status.ACCEPTED, WasteRequest.Status.COMPLETED]


def _get_trunc(granularity):
    return TruncDate("created_at") if granularity == "day" else TruncMonth("created_at")


def _normalize_granularity(request):
    granularity = request.query_params.get("granularity", "month").lower()
    return granularity if granularity in {"day", "month"} else "month"


import datetime

def _format_period(period):
    if isinstance(period, datetime.datetime):
        return period.date().isoformat()
    elif isinstance(period, datetime.date):
        return period.isoformat()
    return str(period)[:10]

def _serialize_timeseries(queryset, period_field, quantity_field=None, amount_field=None):
    data = []
    for row in queryset:
        item = {"period": _format_period(row[period_field])}
        if "count" in row:
            item["count"] = row["count"]
        if quantity_field:
            item["quantity"] = row.get(quantity_field) or Decimal("0.00")
        if amount_field:
            item["amount"] = row.get(amount_field) or Decimal("0.00")
        data.append(item)
    return data


def _build_admin_report_data(granularity):
    period = _get_trunc(granularity)
    sales = WasteRequest.objects.filter(status__in=SALE_STATUSES)

    transactions_over_time = (
        sales.annotate(period=period)
        .values("period")
        .annotate(count=Count("id"), amount=Sum("proposed_price"))
        .order_by("period")
    )
    category_distribution = list(
        WasteListing.objects.values("waste_type")
        .annotate(listing_count=Count("id"), total_quantity=Sum("quantity"))
        .order_by("-listing_count", "-total_quantity", "waste_type")
    )
    sold_listing_ids = WasteRequest.objects.filter(status__in=SALE_STATUSES).values_list(
        "listing_id", flat=True
    ).distinct()

    active_users = defaultdict(set)
    listings_activity = WasteListing.objects.annotate(period=period).values(
        "period", "farmer_id"
    )
    request_activity = WasteRequest.objects.annotate(period=period).values(
        "period", "processor_id", "listing__farmer_id"
    )

    for row in listings_activity:
        active_users[_format_period(row["period"])].add(row["farmer_id"])
    for row in request_activity:
        bucket = active_users[_format_period(row["period"])]
        bucket.add(row["processor_id"])
        bucket.add(row["listing__farmer_id"])

    active_users_over_time = [
        {"period": period_key, "active_users": len(user_ids)}
        for period_key, user_ids in sorted(active_users.items())
    ]

    total_listings = WasteListing.objects.count()
    sold_listings = WasteListing.objects.filter(id__in=sold_listing_ids).count()

    return {
        "granularity": granularity,
        "total_platform_transactions": {
            "total_transactions": sales.count(),
            "total_transaction_value": sales.aggregate(total=Sum("proposed_price"))["total"]
            or Decimal("0.00"),
            "timeline": _serialize_timeseries(
                transactions_over_time, "period", amount_field="amount"
            ),
        },
        "active_users_over_time": active_users_over_time,
        "waste_categories_distribution": [
            {
                "waste_type": row["waste_type"],
                "listing_count": row["listing_count"],
                "total_quantity": row["total_quantity"] or Decimal("0.00"),
            }
            for row in category_distribution
        ],
        "marketplace_liquidity": {
            "total_listings": total_listings,
            "sold_listings": sold_listings,
            "unsold_listings": WasteListing.objects.exclude(id__in=sold_listing_ids).count(),
            "successful_sales": sales.count(),
            "sell_through_rate": round((sold_listings / total_listings), 4)
            if total_listings
            else 0,
        },
    }


class FarmerReportsView(APIView):
    permission_classes = [IsFarmer]

    def get(self, request, *args, **kwargs):
        granularity = _normalize_granularity(request)
        period = _get_trunc(granularity)
        listings = WasteListing.objects.filter(farmer=request.user)
        sales = WasteRequest.objects.filter(listing__farmer=request.user, status__in=SALE_STATUSES)
        sold_listing_ids = sales.values_list("listing_id", flat=True).distinct()

        waste_listed_over_time = (
            listings.annotate(period=period)
            .values("period")
            .annotate(count=Count("id"), quantity=Sum("quantity"))
            .order_by("period")
        )
        revenue_over_time = (
            sales.annotate(period=period)
            .values("period")
            .annotate(count=Count("id"), amount=Sum("proposed_price"))
            .order_by("period")
        )
        most_demanded_waste_types = list(
            WasteRequest.objects.filter(listing__farmer=request.user)
            .values("listing__waste_type")
            .annotate(
                request_count=Count("id"),
                total_quantity_requested=Sum("quantity_requested"),
            )
            .order_by("-request_count", "-total_quantity_requested", "listing__waste_type")
        )

        response = {
            "granularity": granularity,
            "total_waste_listed_over_time": _serialize_timeseries(
                waste_listed_over_time, "period", quantity_field="quantity"
            ),
            "revenue_earned_from_waste_sales": {
                "total_revenue": sales.aggregate(total=Sum("proposed_price"))["total"] or Decimal("0.00"),
                "total_sales": sales.count(),
                "timeline": _serialize_timeseries(revenue_over_time, "period", amount_field="amount"),
            },
            "most_demanded_waste_types": [
                {
                    "waste_type": row["listing__waste_type"],
                    "request_count": row["request_count"],
                    "total_quantity_requested": row["total_quantity_requested"] or Decimal("0.00"),
                }
                for row in most_demanded_waste_types
            ],
            "unsold_vs_sold_listings": {
                "sold": listings.filter(id__in=sold_listing_ids).count(),
                "unsold": listings.exclude(id__in=sold_listing_ids).count(),
                "total": listings.count(),
            },
        }
        return Response(response)


class ProcessorReportsView(APIView):
    permission_classes = [IsProcessor]

    def get(self, request, *args, **kwargs):
        granularity = _normalize_granularity(request)
        period = _get_trunc(granularity)
        purchases = WasteRequest.objects.filter(processor=request.user, status__in=SALE_STATUSES)

        purchased_over_time = (
            purchases.annotate(period=period)
            .values("period")
            .annotate(count=Count("id"), quantity=Sum("quantity_requested"))
            .order_by("period")
        )
        spending_over_time = (
            purchases.annotate(period=period)
            .values("period")
            .annotate(count=Count("id"), amount=Sum("proposed_price"))
            .order_by("period")
        )
        reliable_suppliers = list(
            purchases.values("listing__farmer__id", "listing__farmer__username")
            .annotate(
                successful_transactions=Count("id"),
                total_quantity_supplied=Sum("quantity_requested"),
                total_spend=Sum("proposed_price"),
            )
            .order_by("-successful_transactions", "-total_quantity_supplied", "listing__farmer__username")
        )
        availability_trends = (
            WasteListing.objects.annotate(period=period)
            .values("period")
            .annotate(count=Count("id"), quantity=Sum("quantity"))
            .order_by("period")
        )
        currently_available = WasteListing.objects.filter(
            status__in=[WasteListing.Status.OPEN, WasteListing.Status.REQUESTED]
        )

        response = {
            "granularity": granularity,
            "total_waste_purchased": {
                "total_quantity": purchases.aggregate(total=Sum("quantity_requested"))["total"] or Decimal("0.00"),
                "total_transactions": purchases.count(),
                "timeline": _serialize_timeseries(
                    purchased_over_time, "period", quantity_field="quantity"
                ),
            },
            "spending_trends": {
                "total_spend": purchases.aggregate(total=Sum("proposed_price"))["total"] or Decimal("0.00"),
                "timeline": _serialize_timeseries(spending_over_time, "period", amount_field="amount"),
            },
            "most_reliable_suppliers": [
                {
                    "farmer_id": row["listing__farmer__id"],
                    "farmer_username": row["listing__farmer__username"],
                    "successful_transactions": row["successful_transactions"],
                    "total_quantity_supplied": row["total_quantity_supplied"] or Decimal("0.00"),
                    "total_spend": row["total_spend"] or Decimal("0.00"),
                }
                for row in reliable_suppliers
            ],
            "waste_availability_trends": {
                "currently_available_listings": currently_available.count(),
                "currently_available_quantity": currently_available.aggregate(total=Sum("quantity"))["total"]
                or Decimal("0.00"),
                "timeline": _serialize_timeseries(
                    availability_trends, "period", quantity_field="quantity"
                ),
            },
        }
        return Response(response)


class AdminReportsView(APIView):
    permission_classes = [IsPlatformAdmin]

    def get(self, request, *args, **kwargs):
        granularity = _normalize_granularity(request)
        return Response(_build_admin_report_data(granularity))


@login_required
@user_passes_test(lambda user: user.is_platform_admin)
def admin_dashboard(request):
    if not getattr(request.user, "is_platform_admin", False):
        return HttpResponseForbidden("Admin access required.")

    granularity = _normalize_granularity(request)
    context = _build_admin_report_data(granularity)
    context["granularity_label"] = "Daily" if granularity == "day" else "Monthly"
    context["active_users_latest"] = (
        context["active_users_over_time"][-1]["active_users"]
        if context["active_users_over_time"]
        else 0
    )

    # Admin lists with filters
    user_query = request.GET.get('user_query', '')
    listing_query = request.GET.get('listing_query', '')
    listing_type = request.GET.get('listing_type', '')
    order_query = request.GET.get('order_query', '')

    users = User.objects.all()
    if user_query:
        users = users.filter(Q(username__icontains=user_query) | Q(first_name__icontains=user_query) | Q(last_name__icontains=user_query))

    listings = WasteListing.objects.all()
    listing_q = Q()
    if listing_query:
        listing_q |= Q(waste_type__icontains=listing_query) | Q(notes__icontains=listing_query)
    if listing_type:
        listing_q &= Q(waste_type__icontains=listing_type)
    if listing_q:
        listings = listings.filter(listing_q)

    orders = WasteRequest.objects.all()
    if order_query:
        orders = orders.filter(
            Q(listing__waste_type__icontains=order_query) |
            Q(listing__farmer__username__icontains=order_query)
        )

    context.update({
        'users': users[:100],  # Limit for performance
        'listings': listings[:100],
        'orders': orders[:100],
        'user_query': user_query,
        'listing_query': listing_query,
        'listing_type': listing_type,
        'order_query': order_query,
    })

    return render(request, "reports/admin_dashboard.html", context)


from django.http import HttpResponse
import csv

class AdminUsersCSV(IsPlatformAdminMixin, APIView):
    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        user_query = request.GET.get('user_query', '')
        users = User.objects.all()
        if user_query:
            users = users.filter(Q(username__icontains=user_query) | Q(first_name__icontains=user_query) | Q(last_name__icontains=user_query))

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="admin_users.csv"'
        writer = csv.writer(response)
        writer.writerow(['ID', 'Username', 'Full Name', 'Role', 'Phone', 'Date Joined'])
        for user in users:
            writer.writerow([user.id, user.username, user.full_name, user.role, user.phone_number, user.date_joined])
        return response


class AdminListingsCSV(IsPlatformAdminMixin, APIView):
    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        listing_query = request.GET.get('listing_query', '')
        listing_type = request.GET.get('listing_type', '')
        listings = WasteListing.objects.all()
        listing_q = Q()
        if listing_query:
            listing_q |= Q(waste_type__icontains=listing_query) | Q(notes__icontains=listing_query)
        if listing_type:
            listing_q &= Q(waste_type__icontains=listing_type)
        if listing_q:
            listings = listings.filter(listing_q)

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="admin_listings.csv"'
        writer = csv.writer(response)
        writer.writerow(['ID', 'Waste Type', 'Quantity', 'Farmer', 'Status', 'Created'])
        for listing in listings:
            writer.writerow([listing.id, listing.waste_type, f"{listing.quantity}{listing.unit}", listing.farmer.username, listing.status, listing.created_at])
        return response


class AdminOrdersCSV(IsPlatformAdminMixin, APIView):
    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        order_query = request.GET.get('order_query', '')
        orders = WasteRequest.objects.all()
        if order_query:
            orders = orders.filter(
                Q(listing__waste_type__icontains=order_query) |
                Q(listing__farmer__username__icontains=order_query)
            )

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="admin_orders.csv"'
        writer = csv.writer(response)
        writer.writerow(['ID', 'Listing ID', 'Processor', 'Quantity Requested', 'Status', 'Created'])
        for order in orders:
            writer.writerow([order.id, order.listing.id, order.processor.username, f"{order.quantity_requested}", order.status, order.created_at])
        return response
