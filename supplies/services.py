import json
import logging
import xml.etree.ElementTree as ET

import requests
from django.conf import settings
from django.core.serializers import serialize
from django.db.models import QuerySet
from openai import OpenAI

from supplies.models import Offer, SupplierOffer, Supplier, SupplierCategory

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


def generate_offers_xml(offer_queryset: QuerySet[Offer]):
    # Create the XML structure
    root = ET.Element("catalog")

    print(offer_queryset.count())

    shop = ET.SubElement(root, "shop")

    ET.SubElement(shop, "name").text = "111"  # You can fill in the shop details accordingly
    ET.SubElement(shop, "company").text = "111"
    ET.SubElement(shop, "url").text = "111"

    currencies = ET.SubElement(shop, "currencies")
    ET.SubElement(currencies, "currency", id='UAH', rate='1')

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
            elif field in ['keywords', 'keywords_ua']:
                ET.SubElement(offer_element, field).text = ','.join(value)
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
                if field in ['keywords', 'keywords_ua']:
                    t = ET.SubElement(offer_element, field).text or ''
                    t = t + ',' if t else ''
                    ET.SubElement(offer_element, field).text = t + ','.join(data[field])
                else:
                    ET.SubElement(offer_element, field).text = str(data[field])

    # Convert the ElementTree to a string
    xml_data = ET.tostring(root, encoding="utf-8").decode("utf-8")
    return xml_data


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


class DeeplTranslator:
    def __init__(self, api_key: str):
        self._api_key = api_key

    def translate(self, s: str) -> str:
        resp = requests.post(
            'https://api-free.deepl.com/v2/translate',
            headers={
                'Authorization': f'DeepL-Auth-Key {self._api_key}',
                'Content-Type': 'application/json'
            },
            json={
                'text': [s],
                'target_lang': 'UK'
            },
        )
        logger.info(resp.json())
        return resp.json()['translations'][0]['text']


class OpenAITranslator:
    def __init__(self, client: OpenAI):
        self._client = client

    def translate(self, s: str) -> str:
        comp = self._client.chat.completions.create(
            model="gpt-3.5-turbo",
            max_tokens=600,
            # temperature=0.6,
            timeout=10,
            messages=[
                {"role": "user",
                 "content": """
                         Переклади цей текст українською мовою
                         """},
                {"role": "user", "content": s},
                {"role": "user", "content": f'ПИШИ УКРАЇНСЬКОЮ МОВОЮ'}
            ]
        )
        return comp.choices[0].message.content


class ContentManager:
    def __init__(self, client: OpenAI):
        self._client = client

    def generate_title(self, offer: Offer):
        soffer = offer.supplier_offer
        comp = self._client.chat.completions.create(
            model="gpt-3.5-turbo",
            max_tokens=110,
            # temperature=0.6,
            timeout=10,
            messages=[
                {"role": "user",
                 "content": """
                 Create a concise keyword-rich product title in the format: <product type> <brand> <model> <key information> <features list>. 
                 The title should reflect the main meaning of the product, should not exceed 110 characters, be brief, without any product description. 
                 """},
                {"role": "user", "content": f'{soffer.name}\n{offer.description}\n{soffer.params}'},
                {"role": "user", "content": f'ПИШИ НА РУССКОМ ЯЗЫКЕ'}
            ]
        )
        text = comp.choices[0].message.content
        offer.name = text
        offer.save(update_fields=['name'])

    def generate_description(self, offer: Offer):
        soffer = offer.supplier_offer

        comp = self._client.chat.completions.create(
            model="gpt-3.5-turbo-1106",
            timeout=10,
            max_tokens=600,
            messages=[
                {"role": "user",
                 "content": """
                 Составь описание для товара на основе предоставленной тебе информации. 
                 Средняя длина описания – 400-800 символов
                 """},
                {"role": "user", "content": f'{soffer.name}\n{soffer.description}\n{soffer.params}'},
                {"role": "user", "content": f'ПИШИ НА РУССКОМ ЯЗЫКЕ'}
            ]
        )
        offer.description = comp.choices[0].message.content
        offer.save(update_fields=['description'])


def get_content_manager():
    return ContentManager(OpenAI(**settings.OPENAI_CREDENTIALS))


def get_translator():
    return DeeplTranslator(settings.DEEPL_API_KEY)
