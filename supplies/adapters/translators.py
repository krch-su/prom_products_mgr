import requests
from openai import OpenAI

from supplies import abstract
from supplies.services.content import logger


class DeeplTranslator(abstract.Translator):
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


class OpenAITranslator(abstract.Translator):
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
