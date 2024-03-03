from openai import OpenAI
from supplies import abstract
from supplies.models import SupplierOffer


class OpenAIRewriter(abstract.Rewriter):
    def __init__(self, client: OpenAI):
        self._client = client

    def rewrite_title(self, offer: SupplierOffer) -> str:
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
                {"role": "user", "content": f'{offer.name}\n{offer.description}\n{offer.params}'},
                {"role": "user", "content": f'ПИШИ НА РУССКОМ ЯЗЫКЕ'}
            ]
        )
        return comp.choices[0].message.content

    def rewrite_description(self, offer: SupplierOffer) -> str:
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
                {"role": "user", "content": f'{offer.name}\n{offer.description}\n{offer.params}'},
                {"role": "user", "content": f'ПИШИ НА РУССКОМ ЯЗЫКЕ'}
            ]
        )

        return comp.choices[0].message.content
