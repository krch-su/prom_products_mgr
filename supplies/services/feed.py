import asyncio
import json
import logging
import math
import os
from typing import List, Dict

from bs4 import BeautifulSoup
from lxml import etree as ET

import cv2
import numpy as np
import requests
from _decimal import Decimal
from django.conf import settings
from django.core.serializers import serialize
from django.db.models import QuerySet
from requests import HTTPError
from retry import retry

from supplies.models import SiteCategory, Offer, SupplierCategory, SupplierOffer, Supplier
from supplies.services.images import TextDetector, swt_text_detection

logger = logging.getLogger(__name__)


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


def model_to_json(model, exclude_fields = None):
    exclude_fields = exclude_fields or []
    json_data = serialize('json', [model])
    return {
        k: v for k, v in json.loads(json_data)[0]['fields'].items()
        if k not in exclude_fields
    }


def replace_symbols(input_text):
    replacements = {
        '"': '&quot;',
        '&': '&amp;',
        '>': '&gt;',
        '<': '&lt;',
        "'": '&apos;'
    }

    for symbol, replacement in replacements.items():
        input_text = input_text.replace(symbol, replacement)

    return input_text


def get_offers_data(offer_queryset):
    exclude_fields = ['_id', 'supplier', 'created_at', 'updated_at', 'optPrice', 'category', 'id']

    offers = []
    for offer in offer_queryset:
        offer_result = {}
        offer_data = model_to_json(offer)
        supplier_offer_data = model_to_json(offer.supplier_offer, exclude_fields)
        attrs = {'id': str(offer.pk)}

        category = offer.supplier_offer.category
        if category and category.site_category:
            offer_result['categoryId'] = category.site_category.id

        for k, v in supplier_offer_data.items():
            if k in ['keywords', 'keywords_ua'] and (v or offer_data.get(v, None)):
                val = ', '.join((v or []) + (offer_data.get(k, []) or []))
            elif k == 'price':
                val = math.ceil(offer.price)
            elif k in ['oldprice', 'price_old', 'discount'] and v and offer.price_multiplier:
                v = Decimal(v)
                val = math.ceil(v * offer.price_multiplier)
                if k in ['oldprice', 'price_old'] and v < offer.price:
                    # using 30% discount as fallback if supplier data has wrong old price
                    val = math.ceil(v + v * Decimal(0.3))
            elif isinstance(v, bool):
                val = str(offer_data.get(k, v)).lower()
            elif k == 'pictures':
                val = (offer_data.get(k, []) or []) + (v or [])
            elif (offer_data.get(k, v) or v) is not None:
                val = str(offer_data.get(k, v) or v)
            else:
                continue

            if k in ['id', 'available', 'group_id']:
                attrs[k] = val
            else:
                offer_result[k] = val

        offer_result = {
            k: v for k, v in offer_result.items()
            if k not in attrs
        }

        offer_result['_attrs'] = attrs

        offers.append(offer_result)
    return offers


def gen_xml(offers_data: List[Dict]):
    root = ET.Element("yml_catalog")
    shop = ET.SubElement(root, "shop")
    ET.SubElement(shop, "name").text = "111"  # You can fill in the shop details accordingly
    ET.SubElement(shop, "company").text = "111"
    ET.SubElement(shop, "url").text = "111"
    currencies = ET.SubElement(shop, "currencies")
    ET.SubElement(currencies, "currency", id='UAH', rate='1')
    categories = ET.SubElement(shop, "categories")
    offers = ET.SubElement(shop, "offers")

    categories_qs = SiteCategory.objects.all()

    for c in categories_qs:
        attrs = {'id': str(c.id)}
        if c.parent_category:
            attrs['parentId'] = str(c.parent_category.id)
        category = ET.SubElement(
            categories, "category",
            attrib=attrs
        )
        category.text = c.name

    for o in offers_data:
        offer_el = ET.SubElement(offers, "offer", attrib=o.pop('_attrs'))
        for field, value in o.items():
            if field == 'params':
                params_root = ET.fromstring(f'<root>{value}</root>')
                insert_elements(params_root, offer_el)
            elif field in ['keywords', 'keywords_ua'] and value:
                ET.SubElement(offer_el, field).text = value
            elif field == 'pictures':
                for url in value[:10]:
                    ET.SubElement(offer_el, 'picture').text = str(url)
            elif field in ['description', 'description_ua']:
                ET.SubElement(offer_el, field).text = ET.CDATA(value.replace('\n', '<br/>'))
            else:
                ET.SubElement(offer_el, field).text = str(value)
    return ('<?xml version="1.0" encoding="UTF-8" ?><!DOCTYPE yml_catalog SYSTEM "shops.dtd">' +
            ET.tostring(root, encoding="utf-8").decode("utf-8"))


def generate_offers_xml(offer_queryset: QuerySet[Offer]):
    return gen_xml(get_offers_data(offer_queryset))


def save_offers(xml_data, supplier):
    # Parse XML
    root = ET.fromstring(xml_data)
    existing_categories = SupplierCategory.objects.filter(supplier=supplier).values_list('pk', flat=True)

    categories = []
    for category_element in root.findall(".//categories/category"):
        categories.append(SupplierCategory(
            id=category_element.get('id'),
            supplier=supplier,
            parent_category_id=category_element.get('parentId'),
            name=category_element.text
        ))
    categories = filter(  # removing categories with invalid parents
        lambda x: x.parent_category_id in list(map(lambda c: c.id, categories)) + list(existing_categories),
        categories
    )

    SupplierCategory.objects.bulk_create(
        categories, update_conflicts=True, update_fields=[
            'name',
            'parent_category_id'
        ], unique_fields=['id']
    )

    categories = SupplierCategory.objects.filter(supplier=supplier).values_list('pk', flat=True)

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
            elif field_name == 'categoryId':
                category_id = int(field_value)
                if category_id in categories:
                    offer_data['category_id'] = category_id
            elif field_name in ['keywords', 'keywords_ua'] and field_value is not None:
                offer_data[field_name] = [x.strip() for x in field_value.split(',')]
            elif field_value is not None and field_name in [f.name for f in SupplierOffer._meta.fields]:
                if field_name in ['pickup', 'delivery']:
                    field_value = field_value.lower() == 'true'
                offer_data[field_name] = field_value

        # Create or update Offer and SupplierOffer models
        SupplierOffer.objects.update_or_create(
            id=offer_data.get('id'),
            supplier=supplier,
            defaults=offer_data
        )


def load_offers(supplier: Supplier):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}
    # Download XML content from the URL
    response = requests.get(supplier.feed_url, headers=headers)

    # Check if the request was successful (status code 200)
    if response.status_code != 200:
        response.raise_for_status()

    return save_offers(response.content, supplier=supplier)


def generate_merchant_center_xml():
    """
    This is a temporary solution for generation GMC feed.
    It delegates generation to external service and replaces main image
    :return: content of xml file
    """
    response = requests.get(settings.MERCHANT_CENTER_FEED_URL)

    if response.status_code != 200:
        response.raise_for_status()

    ET.register_namespace('g', 'http://base.google.com/ns/1.0')
    root = ET.fromstring(response.content)
    ns = {'g': 'http://base.google.com/ns/1.0'}

    items = root.findall('.//item')

    text_detector = TextDetector()

    for item in items:
        # Find the image_link and additional_image_link elements
        image_link = item.find('.//g:image_link', ns)
        additional_image_links = item.findall('.//g:additional_image_link', ns)

        for l in additional_image_links:
            resp = requests.get(l.text)
            image_data = np.frombuffer(resp.content, dtype=np.uint8)
            image = cv2.imdecode(image_data, cv2.IMREAD_COLOR)
            if not text_detector.detect_text(image):
                image_link.text = l.text
                break

    path = os.path.join(settings.MEDIA_ROOT, 'supplies/gmc_feed.xml')
    with open(path, 'w') as f:
        f.write(ET.tostring(root, encoding='unicode'))


# async def fetch(url):
#     response = await loop.run_in_executor(None, requests.get, url)
#     return response

async def agenerate_merchant_center_xml():
    """
    This is a temporary solution for generation GMC feed.
    It delegates generation to external service and replaces main image
    :return: content of xml file
    """

    response = await asyncio.to_thread(requests.get, settings.MERCHANT_CENTER_FEED_URL)

    if response.status_code != 200:
        response.raise_for_status()

    ET.register_namespace('g', 'http://base.google.com/ns/1.0')
    root = ET.fromstring(response.content)
    ns = {'g': 'http://base.google.com/ns/1.0'}

    items = root.findall('.//item')

    request_count = 0

    for item in items:
        # Find the image_link and additional_image_link elements
        image_link = item.find('.//g:image_link', ns)
        additional_image_links = item.findall('.//g:additional_image_link', ns)

        for l in additional_image_links:
            resp = await asyncio.to_thread(requests.get, l.text)
            image_data = np.frombuffer(resp.content, dtype=np.uint8)
            image = cv2.imdecode(image_data, cv2.IMREAD_COLOR)
            if len(swt_text_detection(image)) < 10:
                image_link.text = l.text
                break

        request_count += 1
        if request_count % 100 == 0:
            await asyncio.sleep(2)  # Pause for 5 seconds after every 100 requests

    path = os.path.join(settings.MEDIA_ROOT, 'supplies/gmc_feed.xml')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(ET.tostring(root, encoding='utf-8').decode())


@retry(HTTPError, tries=10, delay=1, backoff=2)
def retrieve_lugi_suggested_price(offer: Offer) -> Decimal:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}
    search_url = f'https://lugi.com.ua/search/?search={offer.supplier_offer.vendor_code}'
    response = requests.get(search_url, headers=headers)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')
    els = soup.find_all('div', class_='product-model')
    for el in els:
        if el.text == offer.supplier_offer.vendor_code:
            e = el.parent.find('span', class_='price-rrc__price')
            return Decimal(e.text.split()[0])


def update_lugi_suggested_prices():
    offers = Offer.objects.filter(
        supplier_offer__supplier__name='lugi', active=True, supplier_offer__available=True
    )
    for offer in offers:
        offer.suggested_price = retrieve_lugi_suggested_price(offer)
        offer.save()