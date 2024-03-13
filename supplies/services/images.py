import base64
import colorsys
import logging
import os
from io import BytesIO
from pathlib import Path

import cv2
import numpy as np
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


class TextDetector:
    def __init__(self, model_path='./bin/frozen_east_text_detection.pb'):
        self.net = cv2.dnn.readNet(model_path)

    def detect_text(self, image, score_threshold=0.9):
        blob = cv2.dnn.blobFromImage(image, 1.0, (320, 320), (123.68, 116.78, 103.94), True, False)
        self.net.setInput(blob)
        (scores, geometry) = self.net.forward(["feature_fusion/Conv_7/Sigmoid", "feature_fusion/concat_3"])
        rects, confidences = self.decode_predictions(scores, geometry, score_threshold)
        for rect in rects:
            cv2.rectangle(image, (rect[0], rect[1]), (rect[2], rect[3]), (0, 255, 0), 2)
        cv2.imwrite("text_detection_result.jpg", image)
        return len(rects) > 20

    def decode_predictions(self, scores, geometry, score_threshold):
        (numRows, numCols) = scores.shape[2:4]
        rects = []
        confidences = []

        for y in range(0, numRows):
            scoresData = scores[0, 0, y]
            xData0 = geometry[0, 0, y]
            xData1 = geometry[0, 1, y]
            xData2 = geometry[0, 2, y]
            xData3 = geometry[0, 3, y]
            anglesData = geometry[0, 4, y]

            for x in range(0, numCols):
                score = scoresData[x]
                if score < score_threshold:
                    continue

                offsetX, offsetY = x * 4.0, y * 4.0
                angle = anglesData[x]
                cos = np.cos(angle)
                sin = np.sin(angle)
                h = xData0[x] + xData2[x]
                w = xData1[x] + xData3[x]

                endX = int(offsetX + (cos * xData1[x]) + (sin * xData2[x]))
                endY = int(offsetY - (sin * xData1[x]) + (cos * xData2[x]))
                startX = int(endX - w)
                startY = int(endY - h)

                rects.append((startX, startY, endX, endY))
                confidences.append(score)

        return rects, confidences

def swt_text_detection(image):
    # Convert the image to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Apply Canny edge detection
    edges = cv2.Canny(gray, 100, 200)

    # Perform morphological operations to clean up edges
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)

    # Find contours in the edge image
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Filter contours based on area and aspect ratio
    min_area = 100
    max_area = 5000
    aspect_ratio = 3
    detected_text_regions = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        area = cv2.contourArea(contour)
        if area > min_area and area < max_area and w / h < aspect_ratio:
            detected_text_regions.append((x, y, x + w, y + h))

    return detected_text_regions
