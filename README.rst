****************
Flask-Idempotent
****************

|pypi| |build| |coverage|

-----

Flask-Idempotent is an exceedingly simple (by design) idempotent request handler for Flask. Implemented as an extension, using Redis as both a lock and response datastore for speed and ease of use and implementation, this will help you simply add idempotency to any endpoint on your Flask application.

============
Installation
============

.. code-block:: bash

    $ pip install flask-idempotent

=====
Usage
=====

.. code-block:: python

    from flask import Flask
    my_app = Flask(__name__)
    Idempotent(my_app)

.. code-block:: jinja2

    <form>
      {{ idempotent_input() }}
      <!-- the rest of your form -->
    </form>

And thats it! (well, if the defaults work for you)

============
How it Works
============

Any request that includes **__idempotent_key** in the request arguments or post data, or **X-Idempotent-Key** in the request's headers will be tracked as a idempotent request. This only takes effect for 240 seconds by default, but this is configurable.

When the first request with a key comes in, Flask-Idempotent will attempt to set IDEMPOTENT_{KEY} in redis. It will then process the request like normal, saving the response in redis for future requests to return. It also uses Redis' pub/sub infrastructure to send a notification to any other requests with the same key.

Any subsequent (simultaneous or otherwise) requests will fail to set this key in Redis, as its already set. They will then wait for a pub/sub notification that the master request has finished, retrieve the prior response, and return that.

==================
Why should I care?
==================

You can't trust user input. Thats rule one of web development. This won't beat malicious attempts to attack your form submissions, but it will help when a user submits a page twice, or an api request is sent twice, due to network failure or otherwise. This will prevent those double submissions and any subsequent results of them.

=============
Configuration
=============

Flask-Idempotent requires Redis to function. It defaults to using redis on the local machine, and the following configuration values are available. Just set them in your flask configuration

.. code-block:: python

    # The Redis host URL
    REDIS_URL = 'redis://some-host:6379/'

    # In seconds, the timeout for a slave request to wait for the first to
    #  complete
    IDEMPOTENT_TIMEOUT = 60

    # In seconds, the amount of time to store the master response before
    #  expiration in Redis
    IDEMPOTENT_EXPIRE = 240



.. |pypi| image:: https://img.shields.io/pypi/v/flask-idempotent.svg?style=flat-square&label=latest%20version
    :target: https://pypi.python.org/pypi/flask-idempotent
    :alt: Latest version released on PyPi

.. |coverage| image:: https://img.shields.io/coveralls/DisruptiveLabs/flask-idempotent/master.svg?style=flat-square
    :target: https://coveralls.io/r/DisruptiveLabs/flask-idempotent?branch=master
    :alt: Test coverage

.. |build| image:: https://img.shields.io/travis/DisruptiveLabs/flask-idempotent/master.svg?style=flat-square&label=unix%20build
    :target: http://travis-ci.org/DisruptiveLabs/flask-idempotent
    :alt: Build status of the master branch
