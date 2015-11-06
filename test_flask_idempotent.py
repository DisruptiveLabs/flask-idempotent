import multiprocessing.pool
import threading
import time
import uuid

import requests
import unittest2
from flask import Flask, render_template_string
from werkzeug.serving import make_server

from flask_idempotent import Idempotent

app = Flask(__name__)
idempotent = Idempotent(app)


@app.route("/", methods=['GET', 'POST'])
def handler():
    time.sleep(1)
    return uuid.uuid4().hex


class TestIdempotent(unittest2.TestCase):
    server = None
    thread = None

    @classmethod
    def setUpClass(cls):
        cls.server = make_server('localhost', 5000, app=app, threaded=True)
        cls.thread = threading.Thread(target=cls.server.serve_forever)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join()

    def test_multiple_requests(self):
        key = uuid.uuid4().hex

        def get_result(*args):
            return requests.post("http://localhost:5000/", headers={'X-Idempotent-Key': key}).text

        pool = multiprocessing.pool.ThreadPool(8)
        results = pool.map(get_result, range(4))
        self.assertEqual(len(set(results)), 1, 'All results for idempotent request were not the same')

    def test_different_keys(self):
        key1, key2 = uuid.uuid4().hex, uuid.uuid4().hex

        def get_result(key):
            return lambda idx: requests.post("http://localhost:5000/", headers={'X-Idempotent-Key': key}).text

        pool = multiprocessing.pool.ThreadPool(8)
        map_1 = pool.map_async(get_result(key1), range(4))
        map_2 = pool.map_async(get_result(key2), range(4))

        results_1 = map_1.get()
        results_2 = map_2.get()
        self.assertEqual(len(set(results_1)), 1, 'All results for idempotent request were not the same')
        self.assertEqual(len(set(results_2)), 1, 'All results for idempotent request were not the same')
        self.assertNotEqual(results_1[0], results_2[0], 'Got same result for both idempotent requests')

    def test_non_idempotent(self):
        pool = multiprocessing.pool.ThreadPool(8)
        results = pool.map(lambda idx: requests.post("http://localhost:5000").text, range(5))
        self.assertEqual(len(set(results)), 5)

    def test_jinja2_env(self):
        with app.app_context():
            key = render_template_string("{{ idempotent_key() }}")
            input = render_template_string("{{ idempotent_input() }}")

        # This should not raise an error
        uuid.UUID(hex=key)
        self.assertIn('name="__idempotent_key"', input)
        self.assertIn('type="hidden"', input)
