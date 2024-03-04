from django.db import models
from django.db.models import Q
from django.utils.safestring import mark_safe


class TreeMixin:
    def get_children_filters(self, include_self=True):
        filters = Q(pk=0)
        if include_self:
            filters |= Q(pk=self.pk)
        for c in self.__class__.objects.filter(parent_category=self):
            _r = c.get_children_filters(include_self=True)
            if _r:
                filters |= _r
        return filters

    def get_all_children(self, include_self=True):
        return self.__class__.objects.filter(self.get_children_filters(include_self))


class Supplier(models.Model):
    _id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=255)
    feed_url = models.URLField(max_length=1000)
    active = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class SupplierOffer(models.Model):
    _id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.DO_NOTHING)

    id = models.CharField(max_length=255)
    available = models.BooleanField(default=False)
    group_id = models.BigIntegerField(null=True, blank=True)
    url = models.URLField(null=True)
    optPrice = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    oldprice = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    price_old = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    old_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    discount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    minimum_order_quantity = models.IntegerField(null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    currencyId = models.CharField(max_length=3)
    # categoryId = models.CharField(max_length=20)
    pickup = models.BooleanField(null=True)
    delivery = models.BooleanField(null=True)
    name = models.CharField(max_length=255)
    name_ua = models.CharField(max_length=255)
    vendorCode = models.CharField(max_length=25)
    barcode = models.CharField(max_length=25, blank=True)
    article = models.CharField(max_length=25, blank=True)
    vendor = models.CharField(max_length=64, null=True, blank=True)
    model = models.CharField(max_length=255, null=True, blank=True)
    country_of_origin = models.CharField(max_length=50, null=True, blank=True)
    country = models.CharField(max_length=50, null=True, blank=True)
    description = models.TextField()
    description_ua = models.TextField()
    quantity_in_stock = models.PositiveIntegerField(null=True, blank=True)
    stock_quantity = models.PositiveIntegerField(null=True, blank=True)
    keywords = models.JSONField(null=True)
    keywords_ua = models.JSONField(null=True)
    params = models.TextField(null=True)
    pictures = models.JSONField()
    gtin = models.CharField(max_length=64, null=True, blank=True)
    mpn = models.CharField(max_length=64, null=True, blank=True)

    category = models.ForeignKey(
        'SupplierCategory',
        on_delete=models.DO_NOTHING,
        null=True, blank=True
    )

    @property
    def main_image_tag(self):
        if len(self.pictures):
            return mark_safe(f'<img src="{self.pictures[0]}" height="150" />')
        else:
            return 'No Image'

    @property
    def vendor_code(self):
        return self.vendorCode or self.barcode or self.article

    @property
    def site_category(self):
        return (
            self.category.site_category.name
            if self.category and self.category.site_category
            else ''
        )

    @property
    def category_display(self):
        return self.category.name if self.category else ''

    def __str__(self):
        return self.vendor_code

    class Meta:
        verbose_name = 'Supplier Offer'
        verbose_name_plural = 'Supplier Offers'


class Offer(models.Model):
    _id = models.BigAutoField(primary_key=True)
    supplier_offer: SupplierOffer = models.OneToOneField(
        SupplierOffer,
        on_delete=models.DO_NOTHING,
        related_name='offer'
    )
    active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    group_id = models.BigIntegerField(null=True, blank=True)
    url = models.URLField(null=True, blank=True)
    name = models.CharField(max_length=255, null=True, blank=True)
    name_ua = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    description_ua = models.TextField(null=True, blank=True)
    keywords = models.JSONField(null=True, blank=True)
    keywords_ua = models.JSONField(null=True, blank=True)
    params = models.TextField(null=True, blank=True)
    pictures = models.JSONField(null=True, blank=True)
    category = models.ForeignKey(
        'SiteCategory', on_delete=models.DO_NOTHING,
        null=True, blank=True
    )

    price_multiplier = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )

    @property
    def available(self):
        return self.supplier_offer.available

    @property
    def display_name(self):
        return self.name or self.supplier_offer.name

    @property
    def display_name_ua(self):
        return self.name_ua or self.supplier_offer.name_ua

    @property
    def display_description_ua(self):
        return self.description_ua or self.supplier_offer.description_ua

    @property
    def display_keywords(self):
        return self.keywords + self.supplier_offer.keywords

    @property
    def display_keywords_ua(self):
        return self.keywords_ua + self.supplier_offer.keywords_ua

    @property
    def display_params(self):
        return self.params or self.supplier_offer.params

    @property
    def main_image_tag(self):
        if self.pictures:
            main_image = self.pictures[0]
        elif self.supplier_offer.pictures:
            main_image = self.supplier_offer.pictures[0]
        else:
            main_image = None
        return mark_safe(f'<img src="{main_image}" height="150" />')

    @property
    def vendor_code(self):
        return self.supplier_offer.vendor_code

    @property
    def price(self):
        return self.supplier_offer.price * (self.price_multiplier or 1)

    @property
    def display_category(self):
        return self.supplier_offer.site_category

    @property
    def display_supplier(self):
        return self.supplier_offer.supplier

    class Meta:
        verbose_name = 'Offer'
        verbose_name_plural = 'Offers'


class SiteCategory(models.Model, TreeMixin):
    id = models.BigIntegerField(primary_key=True)
    parent_category = models.ForeignKey(
        'self',
        related_name='children',
        on_delete=models.DO_NOTHING,
        null=True,
        blank=True
    )
    name = models.CharField(max_length=512)

    class Meta:
        verbose_name = 'Site Category'
        verbose_name_plural = 'Site Categories'

    def __str__(self):
        return self.name


class SupplierCategory(models.Model, TreeMixin):
    id = models.BigIntegerField(primary_key=True)
    parent_category = models.ForeignKey(
        'self',
        related_name='children',
        on_delete=models.DO_NOTHING,
        null=True,
    )
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.CASCADE
    )

    site_category = models.ForeignKey(
        SiteCategory,
        null=True,
        on_delete=models.DO_NOTHING,
        related_name='supplier_categories'
    )
    name = models.CharField(max_length=512)

    class Meta:
        verbose_name = 'Supplier Category'
        verbose_name_plural = 'Supplier Categories'

    def __str__(self):
        return f'{self.supplier} | {self.name}'
