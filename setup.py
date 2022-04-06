import pathlib
from setuptools import find_packages, setup

# The directory containing this file
HERE = pathlib.Path(__file__).parent

# The text of the README file
README = (HERE / "README.md").read_text()

# This call to setup() does all the work
setup(
    name="realnet-server",
    version="0.0.8",
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
    packages=["realnet_server", "migrations", "realnet_server.templates", "realnet_server.modules", "realnet_wsgi_loader", "realnet_server.resources"],
    package_data={'migrations': ['alembic.ini', 'README', 'versions/*'], 'realnet_server.templates': ['*'], 'realnet_server.resources': ['*']},
    install_requires=["pynecone==0.0.70",
                      "requests_toolbelt",
                      "python-dotenv",
                      "requests",
                      "flask",
                      "bootstrap-flask",
                      "flask-migrate",
                      "flask-sqlalchemy",
                      "flask-cors",
                      "flask-script",
                      "sqlalchemy-serializer",
                      "shapely",
                      "GeoAlchemy2",
                      "psycopg2-binary",
                      "random-password-generator",
                      "authlib",
                      "pyyaml",
                      "boto3"],
    entry_points={
        "console_scripts": [
            "realnet-server=realnet_server.__main__:main",
        ]
    },
)
