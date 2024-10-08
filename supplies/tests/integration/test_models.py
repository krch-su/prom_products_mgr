import pytest
from supplies.models import Supplier, SupplierOffer, Offer
from ..factories import SupplierFactory, SupplierOfferFactory, OfferFactory


@pytest.mark.django_db
class TestSupplierModel:
    def test_supplier_creation(self):
        supplier = SupplierFactory()
        assert supplier.name is not None
        assert supplier.feed_url is not None
        assert supplier.active is True

    def test_supplier_str(self):
        supplier = SupplierFactory(name="Test Supplier")
        assert str(supplier) == "Test Supplier"


@pytest.mark.django_db
class TestSupplierOfferModel:
    def test_supplier_offer_creation(self):
        offer = SupplierOfferFactory()
        assert offer.supplier is not None
        assert offer.available is True
        assert offer.price is not None
        assert offer.currencyId == 'USD'

    def test_supplier_offer_str(self):
        offer = SupplierOfferFactory(vendorCode="VC123")
        assert str(offer) == "VC123"

    def test_main_image_tag(self):
        offer = SupplierOfferFactory(pictures=["http://image.com/img1.jpg"])
        assert offer.main_image_tag == '<img src="http://image.com/img1.jpg" height="150" />'


@pytest.mark.django_db
class TestOfferModel:
    def test_offer_creation(self):
        offer = OfferFactory()
        assert offer.supplier_offer is not None
        assert offer.active is True

    def test_display_name(self):
        offer = OfferFactory(name="Test Offer Name", supplier_offer__name="Fallback Name")
        assert offer.display_name == "Test Offer Name"

    def test_display_name_fallback(self):
        offer = OfferFactory(name=None, supplier_offer__name="Fallback Name")
        assert offer.display_name == "Fallback Name"

    def test_vendor_code(self):
        offer = OfferFactory(supplier_offer__vendorCode="VC123")
        assert offer.vendor_code == "VC123"

    def test_main_image_tag_with_pictures(self):
        offer = OfferFactory(pictures=["http://image.com/img1.jpg"])
        assert offer.main_image_tag == '<img src="http://image.com/img1.jpg" height="150" />'

    def test_main_image_tag_fallback_to_supplier(self):
        offer = OfferFactory(pictures=[], supplier_offer__pictures=["http://image.com/img1.jpg"])
        assert offer.main_image_tag == '<img src="http://image.com/img1.jpg" height="150" />'

    def test_price_with_multiplier(self):
        offer = OfferFactory(supplier_offer__price=100.0, price_multiplier=1.5)
        assert offer.price == 150.0

    def test_price_without_multiplier(self):
        offer = OfferFactory(supplier_offer__price=100.0, price_multiplier=None)
        assert offer.price == 100.0
