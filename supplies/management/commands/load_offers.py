from django.core.management.base import BaseCommand, CommandError

from supplies.models import Supplier
from supplies.services.feed import load_offers


class Command(BaseCommand):
    def handle(self, *args, **options):
        load_offers(Supplier.objects.filter(name='lugi', active=True).first())
        # load_offers(Supplier.objects.filter(name='dropship-b2b', active=True).first())
