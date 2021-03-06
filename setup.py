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
    packages=["realnet_server", "migrations"],
    package_data={'migrations': ['alembic.ini', 'README', 'versions/*']},
    install_requires=["pynecone==0.0.18",
                      "realnet-core==0.0.2",
                      "requests_toolbelt",
                      "keyring",
                      "python-dotenv",
                      "requests",
                      "flask-migrate",
                      "flask-sqlalchemy",
                      "flask-script",
                      "flask",
                      "authlib",
                      "pyyaml"],
    entry_points={
        "console_scripts": [
            "realnet-server=realnet_server.__main__:main",
        ]
    },
)
