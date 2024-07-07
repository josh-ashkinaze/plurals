from setuptools import setup, find_packages

def read_requirements():
    with open('requirements.txt') as req_file:
        return req_file.read().splitlines()

setup(
    name="plurals",
    version="0.0.1",
    description="A package supporting pluralistic multi-agent simulations.",
    author="Joshua Ashkinaze",
    author_email="josh.ashkinaze@gmail.com",
    url="https://github.com/josh-ashkinaze/plurals",
    packages=find_packages(),
    install_requires=read_requirements(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)