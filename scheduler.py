from datetime import datetime
import schedule
import requests
import time

from lxml import objectify, etree


def prepare_file(file_path):
    # Завантаження XML файлу за посиланням
    xml_url = "https://lugi.shop/products_feed.xml?hash_tag=7a3af7817db1ca8c29213e5dff855207&sales_notes=&product_ids=&label_ids=&exclude_fields=&html_description=0&yandex_cpa=&process_presence_sure=&languages=uk%2Cru&group_ids=&extra_fields=quantityInStock%2Ckeywords"

    # Download XML content from the URL
    response = requests.get(xml_url)

    # Check if the request was successful (status code 200)
    if response.status_code != 200:
        response.raise_for_status()

    root = objectify.fromstring(response.content)
    offers = root.shop.offers

    with open('offer_ids.txt', 'r') as f:
        identifiers = f.read().splitlines()
    print(identifiers)
    for offer in offers.iterchildren():
        # if (
        #         offer.get('available') == "false"
        #         or int(offer.quantity_in_stock) < 5
        #         or int(offer.price) < 400
        # ):
        if offer.get('id') not in identifiers:
            offer.getparent().remove(offer)
        # else:
        #     identifiers.append(offer.get('id'))

    with open(file_path, 'w') as f:
        f.write(etree.tostring(root).decode('ascii'))

    # with open("offer_ids.txt", 'w') as f:
    #     f.write('\n'.join(identifiers))


# prepare_file('result.xml')


def import_file(api_token, file_path):
    # API endpoint for importing a file
    endpoint = "https://my.prom.ua/api/v1/products/import_file"

    # Prepare headers with authorization token
    headers = {"Authorization": f"Bearer {api_token}"}

    # Prepare the request payload
    files = {"file": open(file_path, "rb")}
    data = {
      "url": "string",
      "force_update": False,
      "only_available": True,
      "mark_missing_product_as": "none",
      "updated_fields": [
        "price",
        "presence",
        "quantity_in_stock",
        "discount"
      ]
    }

    # Make the request
    response = requests.post(endpoint, headers=headers, files=files, data=data)

    # Check the response
    if response.status_code == 200:
        result = response.json()
        print("Import process ID:", result["id"])
    else:
        print("Error:", response.json())


def job():
    print(datetime.now(), 'IMPORT STARTED')
    # Replace 'your_api_token' with your actual API token
    api_token = "0b3ef1abc21e3846c848b150a8c4d05244d9b8d0"

    # Replace 'path/to/your/file.xml' with the actual path to your XML file
    file_path = "result.xml"
    prepare_file(file_path)
    # Call the function to import the file
    import_file(api_token, file_path)


# # Schedule the job to run every 4 hours
schedule.every(4).hours.do(job)

# Run the scheduler
while True:
    schedule.run_pending()
    time.sleep(1)

