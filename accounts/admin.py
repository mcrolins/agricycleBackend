from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.urls import path, reverse
from django.shortcuts import render, get_object_or_404
from django.http import Http404, HttpResponseRedirect
from .models import User
from listings.models import WasteListing
from orders.models import WasteRequest

from django.utils.html import format_html
from django.urls import reverse

class ListingInline(admin.TabularInline):
    model = WasteListing
    fields = ('waste_type', 'quantity', 'status', 'created_at')
    readonly_fields = ('waste_type', 'quantity', 'status', 'created_at')
    extra = 0

class RequestInline(admin.TabularInline):
    model = WasteRequest
    fields = ('listing', 'quantity_requested', 'status', 'created_at')
    readonly_fields = ('listing', 'quantity_requested', 'status', 'created_at')
    extra = 0

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    actions = []  # Remove all actions (no make admin/processor/farmer)
    list_display = ('username', 'full_name', 'role', 'phone_number', 'date_joined', 'view_details')
    list_filter = ('role', 'date_joined', 'is_active')
    search_fields = ('username', 'first_name', 'last_name')
    fieldsets = UserAdmin.fieldsets + (
        ('Platform Info', {'fields': ('role', 'phone_number')}),
    )
    inlines = [ListingInline, RequestInline]

    def view_details(self, obj):
        url = reverse('admin:user_details', args=[obj.pk])
        return format_html('<a class="button" href="{}">View Details</a>', url)
    view_details.short_description = ''

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:user_id>/details/', self.admin_site.admin_view(self.user_details_view), name='user_details'),
        ]
        return custom_urls + urls

    def user_details_view(self, request, user_id):
        user = get_object_or_404(User, pk=user_id)
        if not self.has_view_permission(request, obj=user):
            raise Http404
        ctx = {
            **self.admin_site.each_context(request),
            'title': f'User Details: {user.username}',
            'user': user,
            'listings_count': user.waste_listings.count(),
            'requests_count': user.waste_requests.count(),
            'opts': self.model._meta,
            'original': user,
        }
        return render(request, 'admin/accounts/user_details.html', ctx)
