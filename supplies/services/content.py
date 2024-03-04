import logging
from supplies import abstract
from supplies.models import Offer


logger = logging.getLogger(__name__)


class ContentManager:
    def __init__(self, rewriter: abstract.Rewriter):
        self._rewriter = rewriter

    def rewrite_title(self, offer: Offer):
        soffer = offer.supplier_offer
        offer.name = self._rewriter.rewrite_title(soffer)
        offer.save(update_fields=['name'])

    def rewrite_description(self, offer: Offer):
        soffer = offer.supplier_offer
        offer.description = self._rewriter.rewrite_description(soffer)
        offer.save(update_fields=['description'])
