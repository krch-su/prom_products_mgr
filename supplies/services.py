import json
import xml.etree.ElementTree as ET

import requests
from django.core.serializers import serialize
from django.db.models import QuerySet
from lxml import etree

from supplies.models import Offer, SupplierOffer, Supplier, Category


def insert_elements(source_root, target_root):
    for element in source_root:
        # Copy the element from the source tree
        new_element = ET.Element(element.tag, attrib=element.attrib)
        new_element.text = element.text
        new_element.tail = element.tail

        # Recursively insert sub-elements
        insert_elements(element, new_element)

        # Append the new element to the target tree
        target_root.append(new_element)


def generate_offers_xml(offer_queryset: QuerySet[Offer]):
    # Create the XML structure
    root = ET.Element("catalog")

    print(offer_queryset.count())

    shop = ET.SubElement(root, "shop")

    ET.SubElement(shop, "name").text = "111"  # You can fill in the shop details accordingly
    ET.SubElement(shop, "company").text = "111"
    ET.SubElement(shop, "url").text = "111"

    currencies = ET.SubElement(shop, "currencies")
    currency_element = ET.SubElement(currencies, "currency", id='UAH', rate='1')

    # Add currency elements if needed

    # categories = ET.SubElement(shop, "categories")

    # Add category elements if needed

    offers = ET.SubElement(shop, "offers")

    for offer_instance in offer_queryset:
        json_data = serialize('json', [offer_instance])
        data = json.loads(json_data)[0]['fields']

        supplier_data = serialize('json', [offer_instance.supplier_offer])
        supplier_fields = json.loads(supplier_data)[0]['fields']
        # Include all fields from SupplierOffer in the offer element

        offer_element_data = dict(id=str(supplier_fields['id']))
        if data['group_id']:
            offer_element_data['group_id'] = data['group_id']
        offer_element = ET.SubElement(offers, "offer", **offer_element_data)

        for field, value in supplier_fields.items():
            if field in ['id', '_id', 'supplier', 'created_at', 'updated_at']:
                continue

            if field == 'params':
                params_root = ET.fromstring(f'<root>{value}</root>')
                insert_elements(params_root, offer_element)
            elif field == 'pictures':
                for url in value:
                    ET.SubElement(offer_element, 'picture').text = str(url)
            elif value not in [None, ""]:
                ET.SubElement(offer_element, field).text = str(value)

        # Replace overridden fields from Offer
        overridden_fields = ['url', 'name', 'name_ua', 'description', 'description_ua',
                             'keywords', 'keywords_ua', 'params', 'pictures']

        for field in overridden_fields:
            if data[field] not in [None, ""]:
                ET.SubElement(offer_element, field).text = str(data[field])

    # Convert the ElementTree to a string
    xml_data = ET.tostring(root, encoding="utf-8").decode("utf-8")
    return xml_data


def build_hierarchy(elements, parent_id=None):
    result = []

    for element in elements:
        if element['data']['parent_category_id'] == parent_id:
            children = build_hierarchy(elements, parent_id=element['data']['id'])
            if children:
                element['children'] = children
            result.append(element)

    return result


def save_offers(xml_data, supplier):
    # Parse XML
    root = ET.fromstring(xml_data)
    tree_data = []
    for el in root.findall(".//categories/category"):
        tree_data.append({'data': {'id': el.get('id'), 'parent_category_id': el.get('parentId'), 'name': el.text}})
    categories = build_hierarchy(tree_data)
    print(categories)
    Category.load_bulk(categories)

    # return
    # Iterate through offer elements
    for offer_element in root.findall(".//offers/offer"):
        offer_data = {
            'id': offer_element.get('id'),
            'group_id': offer_element.get('group_id'),
            'available': offer_element.get('available') == "true",
            'params': '',
            'pictures': [],
        }

        # Extract data from XML
        for field_element in offer_element:
            field_name = field_element.tag
            field_value = field_element.text
            if field_name == 'param':
                offer_data['params'] += ET.tostring(field_element, encoding='utf-8').decode('utf-8') + '\n'
            elif field_name == 'picture':
                offer_data['pictures'].append(field_value)
            elif field_value is not None:
                if field_name in ['pickup', 'delivery']:
                    field_value = field_value == 'true'
                offer_data[field_name] = field_value

        # Create or update Offer and SupplierOffer models
        SupplierOffer.objects.update_or_create(
            id=offer_data.get('id'),
            supplier=supplier,
            defaults=offer_data
        )


def load_offers(supplier: Supplier):
    # url = "https://dropship-b2b.com.ua/storage/upload/000039030/price_uk.xml"

    # Download XML content from the URL
    response = requests.get(supplier.feed_url)

    # Check if the request was successful (status code 200)
    if response.status_code != 200:
        response.raise_for_status()

    return save_offers(response.content, supplier=supplier)
