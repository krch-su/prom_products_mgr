import base64
import colorsys
import logging
import os
from io import BytesIO
from pathlib import Path

import requests
from PIL import Image, ImageDraw
from django.conf import settings
from django.template.loader import render_to_string
from html2image import Html2Image

from supplies.factories import get_features_extractor

logger = logging.getLogger(__name__)


def add_rainbow_border(img, output_image_path, border_size=20):
    # Get the image dimensions
    width, height = img.size

    # Create a new image with larger dimensions
    new_width = width + 2 * border_size
    new_height = height + 2 * border_size
    new_img = Image.new("RGB", (new_width, new_height))

    # Paste the original image onto the new image
    new_img.paste(img, (border_size, border_size))

    # Create a drawing object
    draw = ImageDraw.Draw(new_img)

    # Define the number of rainbow colors
    num_colors = 100

    # Iterate through the rainbow colors and draw the border
    for i in range(border_size):
        color = colorsys.hsv_to_rgb(i / num_colors, 1.0, 1.0)
        color = tuple(int(c * 255) for c in color)
        draw.rectangle(
            [i, i, new_width - i - 1, new_height - i - 1],
            outline=color
        )

    # Save the result
    new_img.save(output_image_path)


def download_image(url):
    response = requests.get(url)
    if response.status_code == 200:
        return BytesIO(response.content)
    return None


def add_border_to_first_image(request, offer):
    # Check if pictures field is not empty
    if offer.supplier_offer.pictures:
        # Get the first image URL
        first_image_url = offer.supplier_offer.pictures[0]

        # Download the image
        image_content = download_image(first_image_url)

        if image_content:
            # Create an Image object from the downloaded content
            img = Image.open(image_content)

            # Construct the absolute file paths
            output_dir = os.path.join(settings.MEDIA_ROOT, 'supplies/images')
            path = Path(output_dir)
            path.mkdir(parents=True, exist_ok=True)
            output_image_name = f"bordered_{os.path.basename(first_image_url)}"
            output_image_path = os.path.join(output_dir, output_image_name)

            # Apply border and save the modified image
            add_rainbow_border(img, output_image_path)

            # # Update the pictures field with the new URL
            # new_image_url = os.path.join(settings.MEDIA_URL, output_image_name)
            output_url = os.path.join(settings.MEDIA_URL, 'supplies/images')
            # Construct the absolute URL of the modified image
            absolute_url = request.build_absolute_uri(os.path.join(output_url, output_image_name))
            logger.debug(absolute_url)
            offer.pictures = []
            # Update the pictures field with the new URL
            offer.pictures.insert(0, absolute_url)

            # offer.pictures.append(new_image_url)

            # Save the updated offer instance
            offer.save()


def add_infographics_to_firs_image(request, offer):
    if not offer.supplier_offer.pictures:
        return

    first_image_url = offer.supplier_offer.pictures[0]

    # Download the image
    image_content = download_image(first_image_url)
    encoded_image = base64.b64encode(image_content.read()).decode()
    features = get_features_extractor().extract_features(offer)
    html = render_to_string(
        'product_infographics/red_title_yellow_arrows.html',
        {
            'product_photo_b64': encoded_image,
            'product_features': [f.capitalize() for f in features.features],
            'product_title': features.title
        }
    )

    output_name = f"bordered_{os.path.basename(first_image_url)}"  # Replace with the desired output path
    h2i = Html2Image(
        size=(800, 800),
        output_path=os.path.join(settings.MEDIA_ROOT, 'supplies/images'),
        custom_flags=[
                '--default-background-color=00000000',
                '--hide-scrollbars',
                '--no-sandbox',
                '--headless'
            ]
    )
    h2i.screenshot(html_str=html,  save_as=output_name)

    output_url = os.path.join(settings.MEDIA_URL, 'supplies/images')
    # Construct the absolute URL of the modified image
    absolute_url = request.build_absolute_uri(os.path.join(output_url, output_name))
    offer.pictures = []
    # Update the pictures field with the new URL
    offer.pictures.insert(0, absolute_url)

    # offer.pictures.append(new_image_url)

    # Save the updated offer instance
    offer.save()
