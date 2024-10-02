import json
import logging

from openai import OpenAI

from supplies import abstract
from supplies.dto import ProductFeatures
from supplies.models import Offer


logger = logging.getLogger(__name__)

class OpenAIFeaturesExtractor(abstract.FeaturesExtractor):
    def __init__(self, client: OpenAI):
        self._client = client

    def extract_features(self, offer: Offer) -> ProductFeatures:
        comp = self._client.chat.completions.create(
            model="gpt-3.5-turbo",
            max_tokens=110,
            # temperature=0.6,
            timeout=10,
            messages=[
                {"role": "user",
                 "content": """
                    extract 5 most important features(1-2 words) and short title(1-3 words) and create JSON with this data, don't use vendor code or SKU in title. 
                    JSON schema:
                    {
                        title: <title>,
                        features: [feature1, feature2, ...]
                    }
                """},
                {"role": "user", "content": f'{offer.display_name_ua}\n{offer.display_description_ua}'},
                {"role": "user", "content": f'ВІДПОВІДАЙ УКРАЇНСЬКОЮ МОВОЮ'}
            ]
        )
        logger.debug(comp.choices[0].message.content)
        return ProductFeatures(**json.loads(comp.choices[0].message.content))
