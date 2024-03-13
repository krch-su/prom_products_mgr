from django.http import HttpResponse, HttpResponseNotFound, JsonResponse

from django.views.generic import View

from supplies.models import Offer
from supplies.services.feed import generate_offers_xml, generate_merchant_center_xml


class XMLFeedView(View):
    def get(self, request):
        # handle the get request
        return HttpResponse(generate_offers_xml(
            Offer.objects.filter(active=True, supplier_offer__available=True).select_related('supplier_offer')
        ), content_type='application/xml')


class MerchantCenterXMLFeedView(View):
    def get(self, request):
        # handle the get request
        return HttpResponse(generate_merchant_center_xml(), content_type='application/xml')
