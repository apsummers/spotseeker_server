import simplejson as json
import logging
import redis
from django.conf import settings

logger = logging.getLogger(__name__)


def get_json(spots):
    """
    Returns a list of dictionaries containing spot JSON from the Redis cache
    :param spots: A QueryList of Spot models
    :return: a list of Spot JSON dictionaries
    """
    spot_json = []

    if redis_client is None:

        for spot in spots:
            spot_json.append(spot.json_data_structure())

    else:
        pipe = redis_client.pipeline()
        keys = _get_spots_cache_keys(spots)

        for key in keys:
            pipe.exists(key)

        results = pipe.execute()

        to_query = []
        to_build = []

        for x in range(0, len(spots)):
            if results[x]:
                to_query.append(keys[x])
            else:
                to_build.append(spots[x])

        pipe = redis_client.pipeline()

        for key in to_query:
            pipe.get(key)

        results = pipe.execute()

        for result in results:
            spot_json.append(json.loads(result))

        set_pipe = redis_client.pipeline()

        for spot in to_build:
            built_json = spot.json_data_structure()
            spot_json.append(built_json)
            cache_value = json.dumps(built_json)
            set_pipe.set(_get_spot_cache_key(spot), cache_value)

        set_pipe.execute()

    return spot_json


def _get_spot_cache_key(spot):
    return "Spot:" + str(spot.id) + ":" + spot.etag + ":json"


def _get_spots_cache_keys(spots):
    """
    Returns a list of string redis cache keys for the given QuerySet of spots
    :param spots: a QuerySet of Spots
    :return: a list of the cache values in Spots
    """
    ids_etags = spots.values('id', 'etag')
    keys = []

    for dictionary in ids_etags:
        id = dictionary['id']
        etag = dictionary['etag']

        keys.append("Spot:" + str(id) + ":" + etag + ":json")

    return keys


def _has_valid_settings():
    """
    Validates the settings for the spotseeker service Redis connection,
    returns True if the settings are valid and False if they are not
    """
    host = getattr(settings, "REDIS_HOSTNAME", None)
    password = getattr(settings, "REDIS_PASSWORD", None)

    if host is None or password is None:
        return False

    if not isinstance(password, basestring):
        return False

    return True


def _get_redis_connection():
    """
    Returns a StrictRedis client that will handle the Redis connection if
    the Redis server is properly configured and reachable and None if
    there is a failure
    """
    if not _has_valid_settings():
        return None

    host = getattr(settings, "REDIS_HOSTNAME", None)
    password = getattr(settings, "REDIS_PASSWORD", None)

    try:
        client = redis.StrictRedis(host=host)
    except Exception as ex:
        print ex
        logger.error("%s" % ex)
        return None

    return client


redis_client = _get_redis_connection()
