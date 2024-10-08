import pytest

from factories import OfferFactory, SupplierFactory, SupplierCategoryFactory
from supplies.services.feed import model_to_json, replace_symbols, get_offers_data, save_offers
from supplies.models import Offer, SupplierCategory, SupplierOffer
from decimal import Decimal


@pytest.mark.django_db
class TestModelToJson:
    def test_model_to_json_includes_all_fields(self):
        offer = OfferFactory()
        json_data = model_to_json(offer)

        assert 'name' in json_data
        assert 'active' in json_data
        assert 'category' in json_data
        assert 'created_at' in json_data
        assert 'description' in json_data

    def test_model_to_json_excludes_fields(self):
        offer = OfferFactory()
        json_data = model_to_json(offer, exclude_fields=['name'])

        assert 'name' not in json_data


class TestReplaceSymbols:
    def test_replace_symbols_correctly(self):
        input_text = '<Hello & "World">'
        expected_output = '&lt;Hello &amp; &quot;World&quot;&gt;'

        assert replace_symbols(input_text) == expected_output


@pytest.mark.django_db
class TestGetOffersData:
    def test_get_offers_data_generates_correct_data(self):
        offer = OfferFactory(supplier_offer__available=True, supplier_offer__price=50)
        queryset = Offer.objects.filter(pk=offer.pk)
        result = get_offers_data(queryset)

        assert len(result) == 1
        assert result[0]['_attrs']['id'] == str(offer.pk)
        assert result[0]['price'] == 50

    def test_get_offers_data_with_discount(self):
        offer = OfferFactory(supplier_offer__price=50, supplier_offer__discount=10, price_multiplier=Decimal('1.2'))
        queryset = Offer.objects.filter(pk=offer.pk)
        result = get_offers_data(queryset)

        assert result[0]['discount'] == 12


@pytest.mark.django_db
def test_save_offers():
    supplier = SupplierFactory()
    cat = SupplierCategoryFactory(supplier=supplier)
    print(cat.pk)
    # Mock XML data
    xml_data = f"""
    <root>
        <categories>
            <category id="2" parentId="{cat.pk}">Electronics</category>
            <category id="3" parentId="2">Phones</category>
        </categories>
        <offers>
            <offer id="100" available="true">
                <name>iPhone</name>
                <price>1000</price>
                <categoryId>2</categoryId>
                <param name="Color">Black</param>
                <picture>http://example.com/image1.jpg</picture>
            </offer>
        </offers>
    </root>
    """

    save_offers(xml_data, supplier)

    # Validate that categories were saved
    # assert SupplierCategory.objects.filter(supplier=supplier).count() == 2

    # Validate that offer was saved
    offer = SupplierOffer.objects.get(id=100)
    assert offer.price == 1000
    assert offer.name == 'iPhone'
    assert offer.pictures == ['http://example.com/image1.jpg']

