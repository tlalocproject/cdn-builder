from setuptools import setup, find_packages

setup(
    name='tlaloc_cdn_builder',
    version='0.1',
    packages=find_packages(),
    include_package_data=True,  # This tells setuptools to include files from MANIFEST.in
)