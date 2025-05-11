from django.core.management.base import BaseCommand
from django.db.models import Max

from supplies.models import SupplierOffer, Offer


class Command(BaseCommand):
    help = 'Remove duplicate SupplierOffers keeping the latest one and delete related Offers too'

    def handle(self, *args, **kwargs):
        duplicates = SupplierOffer.objects.values('vendorCode', 'barcode', 'article') \
            .annotate(max_created_at=Max('created_at')) \
            .order_by('vendorCode', 'barcode', 'article')

        total_deleted_supplier_offers = 0
        total_deleted_offers = 0

        for duplicate in duplicates:
            vendor_code = duplicate['vendorCode']
            barcode = duplicate['barcode']
            article = duplicate['article']
            max_created_at = duplicate['max_created_at']

            offers = SupplierOffer.objects.filter(
                vendorCode=vendor_code,
                barcode=barcode,
                article=article
            )

            offer_to_keep = offers.filter(created_at=max_created_at).first()
            offers_to_delete = offers.exclude(pk=offer_to_keep.pk) if offer_to_keep else offers

            # Delete related Offer records first
            related_offer_ids = Offer.objects.filter(supplier_offer__in=offers_to_delete).values_list('pk', flat=True)
            deleted_offers = Offer.objects.filter(pk__in=related_offer_ids).delete()[0]

            # Then delete the SupplierOffers
            deleted_supplier_offers = offers_to_delete.delete()[0]

            total_deleted_supplier_offers += deleted_supplier_offers
            total_deleted_offers += deleted_offers

            if deleted_supplier_offers > 0:
                self.stdout.write(self.style.SUCCESS(
                    f'Deleted {deleted_supplier_offers} SupplierOffers and {deleted_offers} related Offers '
                    f'for ({vendor_code}, {barcode}, {article})'
                ))

        self.stdout.write(self.style.SUCCESS(
            f'Finished. Deleted {total_deleted_supplier_offers} duplicate SupplierOffers '
            f'and {total_deleted_offers} related Offers.'
        ))