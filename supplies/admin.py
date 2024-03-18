import json
import logging
import xml.etree.ElementTree as ET

import requests
from _decimal import Decimal
from django import forms
from django.contrib import admin, messages
from django.contrib.admin import SimpleListFilter, RelatedFieldListFilter
from django.contrib.admin.helpers import ActionForm
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.messages import SUCCESS, ERROR
from django.core.handlers.wsgi import WSGIRequest
from django.db.models import Func, IntegerField, F
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.urls import path, reverse
from django.utils.html import format_html
from rangefilter.filters import NumericRangeFilterBuilder

from . import models
from .services.images import add_infographics_to_firs_image, add_border_to_first_image
from .tasks import generate_offer_name, generate_offer_description, generate_content_and_translate, \
    translate_offer

logger = logging.getLogger(__name__)


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
                function='jsonb_array_length',
                output_field=IntegerField()
            )
        )
        if self.value() == 'True':
            return queryset.filter(num_pictures__gt=0)
        elif self.value() == 'False':
            return queryset.filter(num_pictures=0)
        else:
            return queryset


class PublishedFilter(SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = 'Is Published'

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'is_published'

    def lookups(self, request, model_admin):
        return (
            ('True', True),
            ('False', False)
        )

    def queryset(self, request, queryset):
        if self.value() == 'True':
            return queryset.filter(offer__isnull=False)
        elif self.value() == 'False':
            return queryset.filter(offer__isnull=True)
        else:
            return queryset


class CategoryFilter(RelatedFieldListFilter):
    def __init__(self, field, request, params, model, model_admin, field_path):
        self._model = model
        super().__init__(field, request, params, model, model_admin, field_path)

    def queryset(self, request, queryset):
        if not self.lookup_val:
            return queryset
        root = self.field.related_model.objects.get(pk=int(self.lookup_val[0]))
        kw = {f'{self.field_path}__in': root.get_all_children()}

        return queryset.filter(**kw)


class JsonSelectMultiple(forms.SelectMultiple):

    def format_value(self, value):
        value = (json.loads(value) if value else []) or []
        self.choices = zip(value, value)  # hack to get choices displayed
        return value

    def value_from_datadict(self, data, files, name):
        return json.dumps(data.getlist(name))


class OfferForm(forms.ModelForm):
    _json_selects = ['keywords', 'keywords_ua']

    class Meta:
        model = models.Offer
        fields = '__all__'
        widgets = {
            'keywords': JsonSelectMultiple(attrs={'class': 'tag-autocomplete'}),
            'keywords_ua': JsonSelectMultiple(attrs={'class': 'tag-autocomplete'}),
        }
        required = (
            'supplier_offer',
            'active',
        )


class PriceMultiplierForm(ActionForm):
    action = forms.CharField(initial='set_multiplier')
    multiplier = forms.DecimalField()


@admin.register(models.Offer)
class OfferAdmin(admin.ModelAdmin):
    form = OfferForm
    change_form_template = 'admin/supplies/category/change_form.html'
    list_display = (
        'vendor_code',
        'active',
        'display_available',
        'display_name',
        'content_hints',
        'display_supplier',
        'display_category',
        'price',
        'link_to_supplier_offer',
        'main_image_tag',
    )

    search_fields = [
        'name',
        'name_ua',
        'supplier_offer__category__site_category__name',
        'supplier_offer__vendorCode',
        'supplier_offer__barcode',
        'supplier_offer__article'
    ]

    list_filter = [
        "supplier_offer__supplier",
        "active",
        ("supplier_offer__category__site_category", CategoryFilter),
        "supplier_offer__available",
        ("supplier_offer__price", NumericRangeFilterBuilder()),
    ]

    actions = [
        'activate',
        'deactivate',
        'generate_content_and_translate',
        'generate_title',
        'generate_description',
        'translate',
        'add_border',
        'add_infographics',
        'set_multiplier'
    ]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'supplier_offer',
            'supplier_offer__category',
            'supplier_offer__supplier',
            'category',
            'supplier_offer__category__site_category'
        )

    @admin.display(description='Наявність')
    def display_available(self, obj):
        if obj.available:
            icon = '<img src="/static/admin/img/icon-yes.svg" alt="True">'
        else:
            icon = '<img src="/static/admin/img/icon-no.svg" alt="False">'
        return format_html(icon)

    @admin.display(description='Контент')
    def content_hints(self, obj):
        return format_html("""
            <a href="#"><span class="hint  hint--bottom  hint--info  hint--large" data-hint="{name_ua}">name_ua</span></a>
            <a href="#"><span class="hint  hint--bottom  hint--info  hint--large" data-hint="{description_ua}">description_ua</span></a>
            <a href="#"><span class="hint  hint--bottom  hint--info  hint--large" data-hint="{description}">description</span></a>
        """, name_ua=obj.name_ua, description_ua=obj.description_ua, description=obj.description)

    @admin.display(description='Офер постачальника')
    def link_to_supplier_offer(self, obj):
        link = reverse("admin:supplies_supplieroffer_change", args=[obj.supplier_offer._id])
        return format_html('<a href="{}">#{}</a>', link, obj.supplier_offer.vendor_code)

    @admin.action(description="Add border to image")
    def add_border(self, request, queryset):
        for offer in queryset:
            add_border_to_first_image(request, offer)

    @admin.action(description="Add infographics to image")
    def add_infographics(self, request, queryset):
        for offer in queryset:
            add_infographics_to_firs_image(request, offer)

    @admin.action(description="Deactivate offers")
    def deactivate(self, request, queryset):
        queryset.update(active=False)

    @admin.action(description="Activate offers")
    def activate(self, request, queryset):
        queryset.update(active=True)

    @admin.action(description='Generate content and translate')
    def generate_content_and_translate(self, request, queryset):
        generate_content_and_translate.delay(list(queryset.values_list('pk', flat=True)))

    @admin.action(description='Generate title')
    def generate_title(self, request, queryset):
        for offer in queryset:
            generate_offer_name.delay(offer.pk)

    @admin.action(description='Generate description')
    def generate_description(self, request, queryset):
        for offer in queryset:
            generate_offer_description.delay(offer.pk)

    @admin.action(description="Translate")
    def translate(self, request, queryset):
        for offer in queryset:
            translate_offer.delay(offer.pk)

    @admin.action(description="Set Multiplier")
    def set_multiplier(self, request: WSGIRequest, queryset):
        if 'apply' in request.POST:
            form = PriceMultiplierForm(request.POST)
            logger.debug('APPLY IN POST')
            if form.is_valid():
                multiplier = form.cleaned_data['multiplier']
                queryset.update(price_multiplier=multiplier)
                messages.add_message(request, SUCCESS, f'Price multiplier updated')
                return HttpResponseRedirect(request.get_full_path())
        else:
            form = PriceMultiplierForm()

        return render(request, 'admin/supplies/offer/set_multiplier_confirmation.html', {
            'items': queryset.order_by('pk'),
            'form': form,
            'title': u'Your title'
        })

    def autocomplete_keyphrase(self, request):
        term = request.GET.get('term')
        resp = requests.get('https://suggester-ua-prod.evo.run/search_suggester/suggest_tags.js', params={
            'term': term
        })
        suggestions = []
        for s in resp.json():
            suggestions.append({'id': s, 'text': s})
        # print(term)
        # suggestions = [{'id': text, 'text': text} for text in ['sug1', 'sug2']]
        # suggestions = MyModel.objects.filter(tags__contains=term).values_list('tags', flat=True)
        return JsonResponse(list(suggestions), safe=False)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('autocomplete-keyphrase/', self.autocomplete_keyphrase, name='supplies_offer_autocomplete_keyphrase'),
        ]
        return custom_urls + urls

    class Media:
        css = {
            'all': ('hint.min.css', 'sticky_toolbar.css', 'zoom.css')
        }

        js = ('scroll_preserve.js', )


@admin.register(models.SupplierOffer)
class SupplierOfferAdmin(admin.ModelAdmin):
    list_display = (
        'vendor_code',
        'supplier',
        'name',
        'category_display',
        'site_category',
        'price',
        'main_image_tag'
    )
    search_fields = [
        'name',
        'category__name',
        'vendorCode',
        'barcode',
        'article'
    ]

    list_filter = [
        "available",
        "supplier",
        ("category", CategoryFilter),
        ("price", NumericRangeFilterBuilder()),
        HasImageFilter,
        PublishedFilter,
    ]

    actions = ['publish']

    @admin.action(description="Publish offers")
    def publish(self, request, queryset):
        for item in queryset:
            models.Offer.objects.get_or_create(supplier_offer=item)

    class Media:
        css = {
            'all': ('sticky_toolbar.css', )
        }

        js = ('scroll_preserve.js', )


@admin.register(models.Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'active')


class CategoryForm(forms.ModelForm):
    supplier_categories = forms.ModelMultipleChoiceField(
        queryset=models.SupplierCategory.objects.all(),
        widget=FilteredSelectMultiple("SupplierCategory", is_stacked=False),
        required=False,
    )

    def get_initial_for_field(self, field, field_name):
        if field_name == 'supplier_categories':
            return self.instance.supplier_categories.all() if self.instance.pk else []
        else:
            return super().get_initial_for_field(field, field_name)

    def save(self, commit=True):
        instance = super(CategoryForm, self).save(commit=False)
        supplier_categories = self.cleaned_data.get('supplier_categories', [])
        instance.supplier_categories.set(supplier_categories)

        if commit:
            instance.save()

        return instance

    class Meta:
        model = models.SiteCategory
        fields = ['name', 'parent_category', 'supplier_categories']


class CategoriesImportForm(forms.Form):
    file = forms.FileField()


@admin.register(models.SiteCategory)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent_category']
    change_list_template = 'admin/supplies/site_category/change_list.html'
    form = CategoryForm
    search_fields = ['name']
    list_filter = ['parent_category']

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('import-xml/', self.import_xml, name='supplies_sitecategory_import_xml'),
        ]
        return custom_urls + urls

    def import_xml(self, request):
        if request.method == 'POST':
            form = CategoriesImportForm(request.POST, request.FILES)
            if form.is_valid():
                file = form.cleaned_data['file']

                # Use csv_file to read and process the data
                with file.open() as file:
                    root = ET.fromstring(file.read())
                    categories = []
                    for category_element in root.findall(".//categories/category"):
                        categories.append(models.SiteCategory(
                            id=category_element.get('id'),
                            parent_category_id=category_element.get('parentId'),
                            name=category_element.text
                        ))
                    models.SiteCategory.objects.bulk_create(
                        categories, update_conflicts=True, update_fields=[
                            'name',
                            'parent_category_id'
                        ], unique_fields=['id']
                    )

                self.message_user(request, 'Data imported from XML file')
                return HttpResponseRedirect(reverse('admin:supplies_sitecategory_changelist'))


@admin.register(models.SupplierCategory)
class SupplierCategoryAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'supplier',
        'parent_category',
        'site_category'
    ]
