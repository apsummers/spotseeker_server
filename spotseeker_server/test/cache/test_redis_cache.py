import random
from django.test import TestCase
from django.test.utils import override_settings
from spotseeker_server.cache import redis_cache
import fakeredis
from spotseeker_server.models import Spot


@override_settings(
    REDIS_HOST='fake-redis.server.com',
    REDIS_PASSWORD='jasonsfoodyummi')
class RedisTest(TestCase):

    def setUp(self):
        redis_cache.redis_client = fakeredis.FakeStrictRedis()
        self.spots = []

        name = "This is a test spot: {0}".format(random.random())

        spot = Spot()
        spot.name = name
        spot.save()

        self.spots.append(spot)

        key = redis_cache._get_spot_cache_key(spot)
        redis_cache.redis_client.set(key, spot.json_data_structure())

    def test_get_spot_cache_key(self):
        spot = self.spots[0]
        key = redis_cache._get_spot_cache_key(spot)

        should_be = "Spot:" + str(spot.id) + ":" + spot.etag + ":json"

        self.assertEquals(key, should_be)

    def test_get_spots_cache_key(self):
        spot = self.spots[0]
        key = redis_cache._get_spot_cache_key(spot)
        keys = redis_cache._get_spots_cache_keys([self.spots[0]])

        self.assertEquals(key, keys[0])

    def test_has_valid_settings(self):
        self.assertTrue(redis_cache._has_valid_settings())


@override_settings(
    REDIS_HOST='fake-redis.server.com',
    REDIS_PASSWORD=1234)
class BadSettingsRedisTest(TestCase):

    def test_has_valid_settings(self):
        self.assertFalse(redis_cache._has_valid_settings())
