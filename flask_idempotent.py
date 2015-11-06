import pickle
import time

import redis
from flask import _request_ctx_stack, request, abort

try:
    from uwsgi import async_sleep as sleep
except ImportError:
    try:
        from gevent import sleep
    except ImportError:
        try:
            from tornado.gen import sleep
        except ImportError:
            from time import sleep


class Idempotent(object):
    _PROCESSING = '__IDEMPOTENT_PROCESSING'

    def __init__(self, app=None):
        self.app = app
        self._key_finders = [lambda request: request.values.get('__idempotent_key', None),
                             lambda request: request.headers.get('X-Idempotent-Key', None)]
        if app:
            self.init_app(app)

    def init_app(self, app):
        app.config.setdefault("REDIS_URL", "redis://")
        app.before_request(self._before_request)
        app.after_request(self._after_request)

    @property
    def _redis(self):
        return redis.StrictRedis.from_url(self.app.config.get('REDIS_URL'))

    def _find_idempotency_key(self, request):
        for func in self._key_finders:
            key = func(request)
            if key:
                return key

    def _serialize_response(self, response):
        return pickle.dumps(response)

    def _unserialize_response(self, response):
        return pickle.loads(response)

    def response_serializer(self, func):
        setattr(self, '_serialize_response', func)

    def response_unserializer(self, func):
        setattr(self, '_unserialize_response', func)

    def key_finder(self, func):
        self._key_finders.append(func)

    def _before_request(self):
        key = self._find_idempotency_key(request)
        if not key:
            return
        redis_key = 'IDEMPOTENT_{}'.format(key)
        resp = self._redis.set(redis_key, self._PROCESSING, nx=True, ex=60)

        if resp is True:
            # We are the first to get this request... Lets go ahead and run the request
            setattr(_request_ctx_stack.top, '__idempotent_key', key)
            return  # Tell flask to continue
        elif resp is None:
            # Wait for a redis subscription notification
            channel = self._redis.pubsub(ignore_subscribe_messages=True)
            channel.subscribe('IDEMPOTENT_{}'.format(key))

            res = self._redis.get(redis_key)
            if res != self._PROCESSING:
                return self._unserialize_response(res)

            endtime = time.time() + 60
            while time.time() < endtime:
                if channel.get_message(timeout=10):
                    break

            res = self._redis.get(redis_key)
            if res == self._PROCESSING:
                abort(408)
            return self._unserialize_response(res)

    def _after_request(self, response):
        if hasattr(_request_ctx_stack.top, '__idempotent_key'):
            redis_key = 'IDEMPOTENT_{}'.format(getattr(_request_ctx_stack.top, '__idempotent_key'))
            # Save the request in redis, notify, then return
            self._redis.set(redis_key, self._serialize_response(response))
            self._redis.publish(redis_key, 'complete')
        return response
