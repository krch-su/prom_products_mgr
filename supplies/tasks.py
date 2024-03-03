from typing import List

from celery import shared_task, group, chord
from celery.utils.log import get_task_logger
from openai import APITimeoutError

from supplies.models import Offer, Supplier
from supplies.factories import get_content_manager, get_translator
from supplies.services.feed import load_offers

logger = get_task_logger(__name__)


@shared_task(autoretry_for=(APITimeoutError,), retry_kwargs={'max_retries': 5}, retry_backoff=True)
def translate_offer(offer_id):
    offer = Offer.objects.get(pk=offer_id)
    offer.name_ua = get_translator().translate(offer.name)
    offer.description_ua = get_translator().translate(offer.description)
    offer.save()


@shared_task()
def translate_offers(*_, offer_ids: List[int]):
    logger.info(offer_ids)
    logger.info(_)
    for id_ in offer_ids:
        translate_offer.delay(id_)


@shared_task(autoretry_for=(APITimeoutError,), retry_kwargs={'max_retries': 5}, retry_backoff=True)
def generate_offer_name(offer_id):
    get_content_manager().rewrite_title(Offer.objects.get(pk=offer_id))


@shared_task(autoretry_for=(APITimeoutError,), retry_kwargs={'max_retries': 5}, retry_backoff=True)
def generate_offer_description(offer_id, *_):
    logger.info(offer_id)
    logger.info(_)
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

    # name_translates = deepl.translate(list(offers.values_list('name', flat=True)))
    # desc_translates = deepl.translate(list(offers.values_list('description', flat=True)))
    # for i, o in enumerate(offers):
    #     logger.debug(o)
    #     o.description_ua = desc_translates[i]
    #     o.name_ua = name_translates[i]
    #     o.save()
