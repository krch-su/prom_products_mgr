import abc

from supplies.dto import ProductFeatures
from supplies.models import SupplierOffer, Offer


class Rewriter(metaclass=abc.ABCMeta):
    def rewrite_title(self, offer: SupplierOffer) -> str:
        ...

    def rewrite_description(self, offer: SupplierOffer) -> str:
        ...


class Translator(metaclass=abc.ABCMeta):
    def translate(self, s: str) -> str:
        ...


class FeaturesExtractor(metaclass=abc.ABCMeta):
    def extract_features(self, offer: Offer) -> ProductFeatures:
        ...
