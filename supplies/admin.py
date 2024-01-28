from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.db.models import Func, BooleanField, IntegerField, F
from rangefilter.filters import NumericRangeFilterBuilder
from treebeard.admin import TreeAdmin

from . import models
from .models import Offer


class HasImageFilter(SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = 'Has image'

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'has_image'

    def lookups(self, request, model_admin):
        return (
            ('True', True),
            ('False', False)
        )

    def queryset(self, request, queryset):
        queryset = queryset.annotate(
            num_pictures=Func(
                F('pictures'),
                function='json_array_length',
                output_field=IntegerField()
            )
        )
        if self.value() == 'True':
            return queryset.filter(num_pictures__gt=0)
        elif self.value() == 'False':
            return queryset.filter(num_pictures=0)
        else:
            return queryset


@admin.register(models.Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display = ('vendor_code', 'active', 'display_name', 'price', 'main_image_tag')
    list_filter = [
        "supplier_offer__supplier",
        "active"
    ]

    actions = ['activate', 'deactivate']

    @admin.action(description="Deactivate offers")
    def deactivate(self, request, queryset):
        queryset.update(active=False)

    @admin.action(description="Activate offers")
    def activate(self, request, queryset):
        queryset.update(active=True)


@admin.register(models.SupplierOffer)
class SupplierOfferAdmin(admin.ModelAdmin):
    list_display = ('vendor_code', 'name', 'price', 'main_image_tag')
    list_filter = [
        "available",
        "supplier",
        ("price", NumericRangeFilterBuilder()),
        HasImageFilter,
    ]

    actions = ['publish']

    @admin.action(description="Publish offers")
    def publish(self, request, queryset):
        for item in queryset:
            Offer.objects.get_or_create(supplier_offer=item)


@admin.register(models.Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'active')


@admin.register(models.Category)
class CategoryAdmin(TreeAdmin):
    pass
