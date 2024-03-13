import asyncio
from typing import List

from celery import shared_task, chord
from celery.utils.log import get_task_logger
from openai import APITimeoutError

from supplies.factories import get_content_manager, get_translator
from supplies.models import Offer, Supplier
from supplies.services.feed import load_offers, agenerate_merchant_center_xml

logger = get_task_logger(__name__)


@shared_task(autoretry_for=(APITimeoutError,), retry_kwargs={'max_retries': 5}, retry_backoff=True)
def translate_offer(offer_id):
    offer = Offer.objects.get(pk=offer_id)
    offer.name_ua = get_translator().translate(offer.name)
    offer.description_ua = get_translator().translate(offer.description)
    offer.save()


@shared_task()
def translate_offers(*_, offer_ids: List[int]):
    for id_ in offer_ids:
        translate_offer.delay(id_)


@shared_task(autoretry_for=(APITimeoutError,), retry_kwargs={'max_retries': 5}, retry_backoff=True)
def generate_offer_name(offer_id):
    get_content_manager().rewrite_title(Offer.objects.get(pk=offer_id))


@shared_task(autoretry_for=(APITimeoutError,), retry_kwargs={'max_retries': 5}, retry_backoff=True)
def generate_offer_description(offer_id, *_):
    get_content_manager().rewrite_description(Offer.objects.get(pk=offer_id))


@shared_task()
def update_feed(supplier_id: int):
    supplier = Supplier.objects.get(pk=supplier_id)
    load_offers(supplier)


@shared_task()
def generate_content_and_translate(offer_ids: List[int]):
    tasks = []
    for id_ in offer_ids:
        tasks.append(generate_offer_name.s(id_))
        tasks.append(generate_offer_description.s(id_))

    chord(tasks)(translate_offers.s(offer_ids=offer_ids))


# text_detector = TextDetector()
#
#
# @shared_task
# def process_image(*_, image_url):
#     logger.debug(image_url)
#
#     response = requests.get(image_url)
#     image_data = np.frombuffer(response.content, dtype=np.uint8)
#     image = cv2.imdecode(image_data, cv2.IMREAD_COLOR)
#     # resized_image = cv2.resize(image, (200, 200))
#     # Your image processing logic here
#     text_detected = len(swt_text_detection(image)) > 10
#     return image_url if not text_detected else None
#
#
# @shared_task
# def update_image_links(root_string, processed_image_urls):
#     root = ET.fromstring(root_string)
#     ns = {'g': 'http://base.google.com/ns/1.0'}
#     for item, processed_image_url in zip(root.findall('.//item'), processed_image_urls):
#         if processed_image_url:
#             image_link = item.find('.//g:image_link', ns)
#             image_link.text = processed_image_url
#
#     path = os.path.join(settings.MEDIA_ROOT, 'supplies/gmc_feed.xml')
#     with open(path, 'w') as f:
#         f.write(ET.tostring(root, encoding='unicode'))
#
#
# @shared_task
# def generate_merchant_center_xml():
#     """
#     This is a temporary solution to generate feed for GMC.
#     It delegates generation to external service and replaces main image
#     :return: content of xml file
#     """
#     response = requests.get(settings.MERCHANT_CENTER_FEED_URL)
#
#     if response.status_code != 200:
#         response.raise_for_status()
#
#     root_string = response.content.decode('utf-8')
#
#     items = ET.fromstring(root_string).findall('.//item')
#     tasks = []
#
#     for item in items:
#         additional_image_links = item.findall('.//g:additional_image_link', {'g': 'http://base.google.com/ns/1.0'})
#         for l in additional_image_links:
#             tasks.append(process_image.s(image_url=l.text))
#
#     chain(
#         *tasks,
#         update_image_links.s(root_string)
#     ).delay()

@shared_task()
def generate_merchant_center_xml():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(agenerate_merchant_center_xml())
