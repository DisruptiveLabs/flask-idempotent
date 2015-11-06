import pickle
import time
import uuid

import redis
import six
from flask import _request_ctx_stack, request, abort
from jinja2 import Markup

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
    _PROCESSING = b'__IDEMPOTENT_PROCESSING' if six.PY3 else '__IDEMPOTENT_PROCESSING'
    _redis = None

    def __init__(self, app=None):
        self.app = app
        self._key_finders = [lambda request: request.values.get('__idempotent_key', None),
                             lambda request: request.headers.get('X-Idempotent-Key', None)]
        if app:
            self.init_app(app)

    def init_app(self, app):
        self.app = app
        app.config.setdefault("REDIS_URL", "redis://")
        app.config.setdefault("IDEMPOTENT_TIMEOUT", 60)
        app.config.setdefault("IDEMPOTENT_EXPIRE", 240)

        @app.context_processor
        def template_context():
            return {'idempotent_key': self.generate_idempotent_key,
                    'idempotent_input': self.make_idempotent_input}

        app.before_request(self._before_request)
        app.after_request(self._after_request)

    def generate_idempotent_key(self):
        return uuid.uuid4().hex

    def make_idempotent_input(self):
        return Markup('<input type="hidden" name="__idempotent_key" value="%s"/>' % self.generate_idempotent_key())

    @property
    def redis(self):
        if not self._redis:
            self._redis = redis.StrictRedis.from_url(self.app.config.get('REDIS_URL'))
        return self._redis

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
        resp = self.redis.set(redis_key, self._PROCESSING, nx=True, ex=self.app.config.get('IDEMPOTENT_EXPIRE'))

        if resp is True:
            # We are the first to get this request... Lets go ahead and run the request
            setattr(_request_ctx_stack.top, '__idempotent_key', key)
            return  # Tell flask to continue
        elif resp is None:
            # Wait for a redis subscription notification
            channel = self.redis.pubsub(ignore_subscribe_messages=True)
            channel.subscribe('IDEMPOTENT_{}'.format(key))

            res = self.redis.get(redis_key)
            if res != self._PROCESSING:
                return self._unserialize_response(res)

            endtime = time.time() + self.app.config.get('IDEMPOTENT_TIMEOUT')
            while time.time() < endtime:
                if channel.get_message(timeout=10):
                    break

            res = self.redis.get(redis_key)
            if res == self._PROCESSING:
                abort(408)
            return self._unserialize_response(res)

    def _after_request(self, response):
        if hasattr(_request_ctx_stack.top, '__idempotent_key'):
            redis_key = 'IDEMPOTENT_{}'.format(getattr(_request_ctx_stack.top, '__idempotent_key'))
            # Save the request in redis, notify, then return
            self.redis.set(redis_key, self._serialize_response(response), ex=self.app.config.get('IDEMPOTENT_EXPIRE'))
            self.redis.publish(redis_key, 'complete')
        return response
