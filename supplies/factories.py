from django.conf import settings
from openai import OpenAI

from supplies import abstract
from supplies.adapters.features_extractors import OpenAIFeaturesExtractor
from supplies.adapters.rewriters import OpenAIRewriter
from supplies.services.content import ContentManager
from supplies.adapters.translators import OpenAITranslator


def get_content_manager() -> ContentManager:
    return ContentManager(
        OpenAIRewriter(OpenAI(**settings.OPENAI_CREDENTIALS))
    )


def get_translator() -> abstract.Translator:
    return OpenAITranslator(OpenAI(**settings.OPENAI_CREDENTIALS))


def get_features_extractor() -> abstract.FeaturesExtractor:
    return OpenAIFeaturesExtractor(OpenAI(**settings.OPENAI_CREDENTIALS))
