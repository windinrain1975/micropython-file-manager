from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
long_description = fh.read()

setup(
name="micropython-file-manager",
version="0.1.0",
author="Your Name",
author_email="your.email@example.com",
description="A GUI tool for managing files on MicroPython devices",
long_description=long_description,
long_description_content_type="text/markdown",
url="https://github.com/yourusername/micropython-file-manager",
packages=find_packages(),
classifiers=[
"Development Status :: 3 - Alpha",
"Intended Audience :: Developers",
"License :: OSI Approved :: MIT License",
"Operating System :: OS Independent",
"Programming Language :: Python :: 3",
"Programming Language :: Python :: 3.6",
"Programming Language :: Python :: 3.7",
"Programming Language :: Python :: 3.8",
"Programming Language :: Python :: 3.9",
],
python_requires=">=3.6",
install_requires=[
"PyQt5>=5.15.6",
"pyserial>=3.5",
],
entry_points={
"console_scripts": [
"mpfilemanager=mpfiles:main",
],
},
)