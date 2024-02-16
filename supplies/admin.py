import json
import xml.etree.ElementTree as ET

import requests
from django import forms
from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.db.models import Func, IntegerField, F
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import path, reverse
from django.utils.html import format_html
from rangefilter.filters import NumericRangeFilterBuilder

from . import models
from .models import Offer, SupplierCategory
from .tasks import translate, generate_offer_name, generate_offer_description, generate_content_and_translate


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

    search_fields = ['name', 'supplier_offer__category__site_category__name']

    list_filter = [
        "supplier_offer__supplier",
        "active",
        "supplier_offer__category__site_category",
        "supplier_offer__available",
    ]

    actions = [
        'activate',
        'deactivate',
        'generate_content_and_translate',
        'generate_title',
        'generate_description',
        'translate'
    ]

    def display_available(self, obj):
        if obj.available:
            icon = '<img src="/static/admin/img/icon-yes.svg" alt="True">'
        else:
            icon = '<img src="/static/admin/img/icon-no.svg" alt="False">'
        return format_html(icon)

    def content_hints(self, obj):
        return format_html("""
            <a href="#"><span class="hint  hint--bottom  hint--info  hint--large" data-hint="{name_ua}">name_ua</span></a>
            <a href="#"><span class="hint  hint--bottom  hint--info  hint--large" data-hint="{description_ua}">description_ua</span></a>
            <a href="#"><span class="hint  hint--bottom  hint--info  hint--large" data-hint="{description}">description</span></a>
        """, name_ua=obj.name_ua, description_ua=obj.description_ua, description=obj.description)

    def link_to_supplier_offer(self, obj):
        link = reverse("admin:supplies_supplieroffer_change", args=[obj.supplier_offer._id])
        return format_html('<a href="{}">#{}</a>', link, obj.supplier_offer.vendor_code)

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
        translate.delay(list(queryset.values_list('pk', flat=True)))

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
            'all': ('hint.min.css', 'sticky_toolbar.css')
        }

        js = ('scroll_preserve.js', )


@admin.register(models.SupplierOffer)
class SupplierOfferAdmin(admin.ModelAdmin):
    list_display = (
        'vendor_code',
        'name',
        'category_display',
        'site_category',
        'price',
        'main_image_tag'
    )
    search_fields = ['name', 'category__name']

    list_filter = [
        "available",
        "supplier",
        ("price", NumericRangeFilterBuilder()),
        HasImageFilter,
        "category",

    ]

    actions = ['publish']

    @admin.action(description="Publish offers")
    def publish(self, request, queryset):
        for item in queryset:
            Offer.objects.get_or_create(supplier_offer=item)


@admin.register(models.Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'active')


class CategoryForm(forms.ModelForm):
    supplier_categories = forms.ModelMultipleChoiceField(
        queryset=SupplierCategory.objects.all(),
        widget=FilteredSelectMultiple("SupplierCategory", is_stacked=False),
        required=False,
    )

    def get_initial_for_field(self, field, field_name):
        if field_name == 'supplier_categories':
            return self.instance.supplier_categories.all()
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
    change_list_template = 'admin/supplies/site_category/change_list.html'
    form = CategoryForm
    search_fields = ['name']

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
                    print(categories)
                    models.SiteCategory.objects.bulk_create(
                        categories, update_conflicts=True, update_fields=[
                            'name',
                            'parent_category_id'
                        ], unique_fields=['id']
                    )

                self.message_user(request, 'Data imported from XML file')
                return HttpResponseRedirect(reverse('admin:supplies_sitecategory_changelist'))
        # else:
        #     form = CategoriesImportForm()
        #
        # context = dict(
        #     self.admin_site.each_context(request),
        #     form=form,
        # )
        #
        # return self.render_change_list(request, context)


@admin.register(models.SupplierCategory)
class SupplierCategoryAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'supplier',
        'parent_category',
        'site_category'
    ]
