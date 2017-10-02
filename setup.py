from setuptools import setup, find_packages

setup(
    name='omgifol',
    version='0.1.0',
    description="A Python library for manipulation of Doom WAD files",
    maintainer="Jernej Kos",
    maintainer_email="jernej@kos.mx",
    url='https://github.com/kostko/omgifol',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Science/Research',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
    ],
    packages=find_packages(exclude=('demo',)),
    install_requires=[
        'six>=1.10.0',
    ],
)
