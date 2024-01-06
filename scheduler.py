import logging
import threading
from datetime import datetime
from http.server import SimpleHTTPRequestHandler
from socketserver import TCPServer

import schedule
import requests
import time

from lxml import objectify, etree


class XMLHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        # Specify the path to your dynamically generated XML file
        xml_file_path = 'result.xml'

        if self.path == '/feed.xml':
            # Set the content type to XML
            self.send_response(200)
            self.send_header('Content-type', 'application/xml')
            self.end_headers()

            # Open and send the content of the XML file
            with open(xml_file_path, 'rb') as f:
                self.wfile.write(f.read())


def get_lugi_xml():
    # Завантаження XML файлу за посиланням
    lugi_url = "https://lugi.shop/products_feed.xml?hash_tag=7a3af7817db1ca8c29213e5dff855207&sales_notes=&product_ids=&label_ids=&exclude_fields=&html_description=0&yandex_cpa=&process_presence_sure=&languages=uk%2Cru&group_ids=&extra_fields=quantityInStock%2Ckeywords"

    # Download XML content from the URL
    response = requests.get(lugi_url)

    # Check if the request was successful (status code 200)
    if response.status_code != 200:
        response.raise_for_status()

    root = objectify.fromstring(response.content)
    offers = root.shop.offers

    with open('offer_ids.txt', 'r') as f:
        identifiers = f.read().splitlines()

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
    return root


def get_db2b_xml():
    # Завантаження XML файлу за посиланням
    url = "https://dropship-b2b.com.ua/storage/upload/000039030/price_uk.xml"

    # Download XML content from the URL
    response = requests.get(url)

    # Check if the request was successful (status code 200)
    if response.status_code != 200:
        response.raise_for_status()

    return objectify.fromstring(response.content)
    # offers = root.shop.offers
    #
    # with open('offer_ids.txt', 'r') as f:
    #     identifiers = f.read().splitlines()

    # for offer in offers.iterchildren():
    #     # if (
    #     #         offer.get('available') == "false"
    #     #         or int(offer.quantity_in_stock) < 5
    #     #         or int(offer.price) < 400
    #     # ):
    #     if offer.get('id') not in identifiers:
    #         offer.getparent().remove(offer)
        # else:
        #     identifiers.append(offer.get('id'))
    # return root


def prepare_file(file_path):
    lugi_xml = get_lugi_xml()
    db2b_xml = get_db2b_xml()

    # offers = lugi_xml.shop.categories
    # offers = lugi_xml.shop.offers

    for category in db2b_xml.shop.categories:
        lugi_xml.shop.categories.append(category)

    for offer in db2b_xml.shop.offers:
        lugi_xml.shop.offers.append(offer)

    with open(file_path, 'w') as f:
        f.write(etree.tostring(lugi_xml).decode('ascii'))

    # with open("offer_ids.txt", 'w') as f:
    #     f.write('\n'.join(identifiers))


# prepare_file('result.xml')


# def import_file(api_token, file_path):
#     # API endpoint for importing a file
#     endpoint = "https://my.prom.ua/api/v1/products/import_file"
#
#     # Prepare headers with authorization token
#     headers = {"Authorization": f"Bearer {api_token}"}
#
#     # Prepare the request payload
#     files = {"file": open(file_path, "rb")}
#     data = {
#       "force_update": False,
#       "only_available": True,
#       "mark_missing_product_as": "none",
#       "updated_fields": [
#         "price",
#         "presence",
#         "quantity_in_stock",
#         "discount"
#       ]
#     }
#
#     # Make the request
#     response = requests.post(endpoint, headers=headers, files=files, data=data)
#
#     # Check the response
#     if response.status_code == 200:
#         result = response.json()
#         logging.info("Import process ID:", result["id"])
#     else:
#         response.raise_for_status()


def job():
    print(datetime.now(), 'PREPARING FILE')
    # Replace 'your_api_token' with your actual API token
    # api_token = "0b3ef1abc21e3846c848b150a8c4d05244d9b8d0"

    # Replace 'path/to/your/file.xml' with the actual path to your XML file
    file_path = "result.xml"
    try:
        prepare_file(file_path)
        # Call the function to import the file
        # import_file(api_token, file_path)
    except Exception as ex:
        logging.exception(ex)


# # # Schedule the job to run every 4 hours
# schedule.every(4).hours.do(job)
#
# # Run the scheduler
# while True:
#     logging.info('Scheduler started')
#     schedule.run_pending()
#     time.sleep(1)
#

def run_server():
    # Start the HTTP server
    host = '37.233.102.20/'
    port = 8080
    server_address = (host, port)
    httpd = TCPServer(server_address, XMLHandler)

    print(f"Serving XML file at http://{host}:{port}")

    try:
        # Run the HTTP server in a separate thread
        httpd.serve_forever()
    except KeyboardInterrupt:
        # Handle KeyboardInterrupt to gracefully shut down the server
        print("\nServer stopped.")
        httpd.shutdown()


if __name__ == '__main__':
    job()
    # Schedule the job to run every hour
    schedule.every().second.do(job)

    # Start the HTTP server in a separate thread
    server_thread = threading.Thread(target=run_server)
    server_thread.start()

    try:
        while True:
            # Run scheduled jobs
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        # Handle KeyboardInterrupt to gracefully shut down the scheduled jobs
        print("\nScheduled jobs stopped.")

    # Wait for the server thread to finish
    server_thread.join()
