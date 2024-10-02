from django.core.management.base import BaseCommand, CommandError
from django.db.models import ExpressionWrapper, F, FloatField, Value
from django.db.models.functions import Coalesce

from supplies.models import Supplier, Offer
from supplies.services.feed import load_offers


def multiply_and_update_field(model_queryset, field_name, multiplier):
    # Use ExpressionWrapper to handle the multiplication, and FloatField to handle possible null values
    model_queryset.update(
        **{f'{field_name}': Coalesce(
            ExpressionWrapper(
                F(field_name) * multiplier, output_field=FloatField()),
            Value(multiplier)
        )}
    )

class Command(BaseCommand):
    def handle(self, *args, **options):
        multiply_and_update_field(Offer.objects.all(), 'price_multiplier', 1.2)
        # load_offers(Supplier.objects.filter(name='lugi', active=True).first())
        # load_offers(Supplier.objects.filter(name='dropship-b2b', active=True).first())
