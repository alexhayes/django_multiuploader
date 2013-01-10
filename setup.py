from distutils.core import setup
from setuptools import find_packages

setup(
    name='django-multiuploader',
    version='1.3.0',
    author='Iurii Garmash',
    author_email='garmon1@gmail.com',
    packages=find_packages(),
    include_package_data=True,
    scripts=[],
    url='https://github.com/garmoncheg/django_multiuploader',
    description='Multiple uploads for Django using jQuery File Upload',
    long_description=open('README').read(),
    install_requires=[
        'Django>=1.5.0',
        'sorl-thumbnail>=11.12',
    ],
)