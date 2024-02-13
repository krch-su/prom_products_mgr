from typing import List

from celery import shared_task
from celery.utils.log import get_task_logger

from supplies.integrations.deepl_batch import DeepLCLI
from supplies.models import Offer
from supplies.services import get_content_manager


@shared_task
def translate(offer_ids: List[int]):
    logger = get_task_logger(__name__)
    deepl = DeepLCLI('ru', "uk")
    logger.info(offer_ids)
    offers = Offer.objects.filter(pk__in=offer_ids)
    name_translates = deepl.translate(list(offers.values_list('name', flat=True)))
    desc_translates = deepl.translate(list(offers.values_list('description', flat=True)))
    for i, o in enumerate(offers):
        logger.debug(o)
        o.description_ua = desc_translates[i]
        o.name_ua = name_translates[i]
        o.save()


@shared_task()
def generate_offer_name(offer_id):
    get_content_manager().generate_title(Offer.objects.get(pk=offer_id))


@shared_task()
def generate_offer_description(offer_id):
    get_content_manager().generate_description(Offer.objects.get(pk=offer_id))


@shared_task()
def update_feeds():
    pass  # todo


