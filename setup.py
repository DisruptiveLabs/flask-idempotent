"""
Flask-Idempotent
--------------

Idempotent requests for Flask applications.
"""
from setuptools import setup


setup(
    name='Flask-Idempotent',
    version='0.0.1',
    url='http://github.com/DisruptiveLabs/flask-idempotent',
    license='MIT',
    author='Franklyn Tackitt',
    author_email='frank@comanage.com',
    description='Idempotent requests for Flask applications',
    long_description=__doc__,
    py_modules=['flask_idempotent'],
    zip_safe=False,
    include_package_data=True,
    platforms='any',
    install_requires=[
        'Flask>=0.9',
        'redis'
    ],
    tests_require=[
        'coverage',
        'nose',
        'requests',
        'unittest2'
    ],
    test_suite='nose.collector',
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ]
)
