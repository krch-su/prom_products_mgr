from django.core.management.base import BaseCommand, CommandError

from supplies.models import Supplier
from supplies.services import load_offers


class Command(BaseCommand):
    def handle(self, *args, **options):
        load_offers(Supplier.objects.filter(name='prom-categories', active=True).first())
        # load_offers(Supplier.objects.filter(name='dropship-b2b', active=True).first())
