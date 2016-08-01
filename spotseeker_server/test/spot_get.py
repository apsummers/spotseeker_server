""" Copyright 2012, 2013 UW Information Technology, University of Washington

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""

from django.test import TestCase
from django.conf import settings
from django.test.client import Client
from spotseeker_server.models import Spot, SpotExtendedInfo, Item,\
                                     ItemExtendedInfo
import simplejson as json
from django.test.utils import override_settings
from mock import patch
from spotseeker_server import models


@override_settings(
    SPOTSEEKER_AUTH_MODULE='spotseeker_server.auth.all_ok',
    SPOTSEEKER_SPOT_FORM='spotseeker_server.default_forms.spot.'
                         'DefaultSpotForm')
class SpotGETTest(TestCase):

    def setUp(self):
        # create a spot without items
        spot = Spot.objects.create(name="This is for testing GET",
                                   latitude=55,
                                   longitude=30)

        # create a spot that will contain items for testing the item json
        spot_with_items = Spot.objects.create(name="This is for testing items"
                                              " GET",
                                              latitude=55,
                                              longitude=30)

        spot_with_items.save()

        self.items = []
        self.extended_data = []
        # create some items for testing
        for i in range(0, 10):
            new_item = Item.objects.create(name="Item" + str(i),
                                           spot=spot_with_items,
                                           category="Laptops",
                                           subcategory="Macbooks")

            for dictdata in range(1, 3):
                extended_data = ItemExtendedInfo()
                extended_data.item = new_item
                extended_data.key = "key " + str(dictdata)
                extended_data.value = "value " + str(dictdata)
                extended_data.save()
                self.extended_data.append(extended_data)
            self.items.append(new_item)
            new_item.save()

        self.spot_with_items = spot_with_items
        self.spot = spot
        spot.save()

    def tearDown(self):
        self.spot.delete()

    def test_invalid_id(self):
        """
        Tests a string instead of a numeric ID for spot retreival.
        """
        c = Client()
        url = "/api/v1/spot/bad_id"
        response = c.get(url)
        self.assertEqual(response.status_code,
                         404,
                         "Rejects a non-numeric id")

    def test_invalid_id_too_high(self):
        """
        Tests that a 404 will be returned for a spot that does not exist
        """
        c = Client()
        url = "/api/v1/spot/%s" % (self.spot.pk + 10000)
        response = c.get(url)
        self.assertEqual(response.status_code, 404, "Spot ID too high")

    def test_content_type(self):
        """
        Tests that the content type for the spot get is application/json
        """
        c = Client()
        url = "/api/v1/spot/%s" % self.spot.pk
        response = c.get(url)
        # import pdb; pdb.set_trace()
        self.assertEqual(response["Content-Type"], "application/json")

    def test_etag(self):
        """
        Tests to ensure that the etag field is present in the spot
        """
        c = Client()
        url = "/api/v1/spot/%s" % self.spot.pk
        response = c.get(url)
        self.assertEqual(response["ETag"], self.spot.etag)

    def test_invalid_params(self):
        """
        Tests the GET with invalid parameters.
        """
        c = Client()
        url = "/api/v1/spot/%s" % self.spot.pk
        response = c.get(url, {'bad_param': 'does not exist'},)
        self.assertEqual(response.status_code, 200)
        spot_dict = json.loads(response.content)
        returned_spot = Spot.objects.get(pk=spot_dict['id'])
        self.assertEqual(returned_spot, self.spot)

    def test_valid_id(self):
        c = Client()
        url = "/api/v1/spot/%s" % self.spot.pk
        response = c.get(url)
        spot_dict = json.loads(response.content)
        returned_spot = Spot.objects.get(pk=spot_dict['id'])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(returned_spot, self.spot)

    def test_empty_items(self):
        """
        Tests to ensure that a Spot with no items present will have an empty
        list in their JSON respresenting items.
        """
        c = Client()
        url = "/api/v1/spot/%s" % self.spot.pk
        response = c.get(url)
        spot_dict = json.loads(response.content)
        self.assertTrue("items" in spot_dict)
        self.assertTrue(len(spot_dict["items"]) == 0, "")

    def test_valid_item_json(self):
        """
        Tests to make sure a Spot json is valid by comparing it with the
        item model.
        """
        c = Client()
        url = "/api/v1/spot/%s" % self.spot_with_items.pk
        response = c.get(url)
        spot_dict = json.loads(response.content)
        items = spot_dict["items"]
        self.assertTrue(len(items) == 10)
        for item in items:
            # assert that the Spot json contains the Item
            for original_item_model in self.items:
                if item['id'] == original_item_model.id:
                    item_model = original_item_model
                    for extended_data_items in self.extended_data:
                        if item_model == extended_data_items.item:
                            item_extended_info = extended_data_items

            self.assertTrue(item_model is not None)
            self.assertTrue('name' in item)
            self.assertTrue(item['name'] == item_model.name)

            # assert Item category and subcategory
            self.assertTrue(item['category'] == item_model.category)
            self.assertTrue(item['subcategory'] == item_model.subcategory)
            self.assertTrue('extended_info' in item)
            for key in item['extended_info']:
                if key == item_extended_info.key:
                    self.assertTrue(item['extended_info'][key] ==
                                    item_extended_info.value)
