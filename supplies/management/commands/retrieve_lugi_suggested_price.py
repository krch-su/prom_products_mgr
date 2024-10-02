from django.core.management.base import BaseCommand, CommandError
from django.db.models import ExpressionWrapper, F, FloatField, Value
from django.db.models.functions import Coalesce

from supplies.models import Supplier, Offer
from supplies.services.feed import load_offers, retrieve_lugi_suggested_price


class Command(BaseCommand):
    def handle(self, *args, **options):
        offer = Offer.objects.filter(active=True, supplier_offer__supplier__name='lugi').first()
        print(offer.name)
        print(offer.supplier_offer.price)
        print(retrieve_lugi_suggested_price(offer))

