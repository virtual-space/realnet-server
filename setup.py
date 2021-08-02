import pathlib
from setuptools import find_packages, setup

# The directory containing this file
HERE = pathlib.Path(__file__).parent

# The text of the README file
README = (HERE / "README.md").read_text()

# This call to setup() does all the work
setup(
    name="realnet-server",
    version="0.0.1",
    description="Realnet server",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/virtual-space/realnet-server",
    author="Marko Laban",
    author_email="marko.laban@l33tsystems.com",
    license="BSD",
    classifiers=[
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
    ],
    packages=["realnet_server", "migrations", "realnet_server.templates", "realnet_server.modules"],
    package_data={'migrations': ['alembic.ini', 'README', 'versions/*'], 'realnet_server.templates': ['*']},
    install_requires=["pynecone==0.0.64",
                      "requests_toolbelt",
                      "keyring",
                      "python-dotenv",
                      "requests==2.23.0",
                      "flask-migrate",
                      "flask-sqlalchemy",
                      "sqlalchemy-serializer",
                      "GeoAlchemy2",
                      "psycopg2-binary",
                      "flask-script",
                      "flask==1.1.2",
                      "authlib",
                      "loginpass",
                      "bootstrap-flask",
                      "pyyaml"],
    entry_points={
        "console_scripts": [
            "realnet-server=realnet_server.__main__:main",
        ]
    },
)
