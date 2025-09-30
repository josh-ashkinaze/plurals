from setuptools import setup, find_packages

def read_requirements():
    with open('requirements.txt') as req_file:
        return req_file.read().splitlines()

setup(
    name="plurals",
    version="0.2.33.3",
    description="A package for simulated social ensembles.",
    long_description=open('README.md').read(),
    long_description_content_type="text/markdown",
    author="Joshua Ashkinaze",
    author_email="josh.ashkinaze@gmail.com",
    url="https://github.com/josh-ashkinaze/plurals",
    packages=find_packages(),
    include_package_data=True,
    install_requires=read_requirements(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    project_urls={
        "Homepage": "https://github.com/josh-ashkinaze/plurals",
        "Documentation": "https://josh-ashkinaze.github.io/plurals",
    },
    python_requires='>=3.6',
)


