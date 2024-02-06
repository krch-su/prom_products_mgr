import requests


class BukvarixAPI:
    URL = 'http://api.bukvarix.com/v1/keywords/'
    api_key = 'free'
    limit = 100

    def __init__(self):
        pass

    def get_keywords(self, term: str):
        resp = requests.get(self.URL, params={
            'api_key': self.api_key,
            'result_count': self.limit,
            'q': term,
            'report_type': 'json'
        })
        print(resp)


if __name__ == '__main__':
    api = BukvarixAPI()
    api.get_keywords('нож туристический')