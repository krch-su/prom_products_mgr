
import factory
from django.utils import timezone
from supplies.models import Supplier, SupplierOffer, Offer, SiteCategory, SupplierCategory


class SupplierFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Supplier

    name = factory.Faker('company')
    feed_url = factory.Faker('url')
    active = True


class SupplierOfferFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SupplierOffer

    supplier = factory.SubFactory(SupplierFactory)
    id = factory.Faker('uuid4')
    available = True
    price = factory.Faker('pydecimal', left_digits=4, right_digits=2, positive=True)
    currencyId = 'USD'
    name = factory.Faker('word')
    name_ua = factory.Faker('word')
    vendorCode = factory.Faker('word')
    description = factory.Faker('text')
    pictures = factory.List([factory.Faker('image_url')])
    created_at = factory.LazyFunction(timezone.now)
    updated_at = factory.LazyFunction(timezone.now)


class SiteCategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SiteCategory

    id = factory.Faker('pyint')
    name = factory.Faker('word')


class SupplierCategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SupplierCategory

    id = factory.Faker('pyint')
    supplier = factory.SubFactory(SupplierFactory)
    site_category = factory.SubFactory(SiteCategoryFactory)
    name = factory.Faker('word')


class OfferFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Offer

    supplier_offer = factory.SubFactory(SupplierOfferFactory)
    active = True
    name = factory.Faker('word')
    name_ua = factory.Faker('word')
    description = factory.Faker('text')
    pictures = factory.List([factory.Faker('image_url')])
    created_at = factory.LazyFunction(timezone.now)
    updated_at = factory.LazyFunction(timezone.now)
