#!/usr/bin/env python3
"""
Setup script for Network Automation Request Sender
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_path = Path(__file__).parent / "README.md"
with open(readme_path, "r", encoding="utf-8") as f:
    long_description = f.read()

# Read requirements
requirements_path = Path(__file__).parent / "requirements.txt"
with open(requirements_path, "r", encoding="utf-8") as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="network-automation-sender",
    version="1.0.0",
    author="Network Automation Team",
    author_email="team@networkautomation.com",
    description="A sophisticated network automation system for HTTP/HTTPS request handling",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-org/network-automation-sender",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Internet :: WWW/HTTP :: HTTP Servers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Networking",
        "Topic :: System :: Systems Administration",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.3",
            "pytest-asyncio>=0.21.1",
            "pytest-cov>=4.1.0",
            "black>=23.11.0",
            "flake8>=6.1.0",
            "mypy>=1.7.1",
        ],
        "docs": [
            "sphinx>=7.2.6",
            "sphinx-rtd-theme>=1.3.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "network-automation=main:main",
        ],
    },
    package_data={
        "": ["*.yaml", "*.yml", "*.json"],
    },
    include_package_data=True,
    zip_safe=False,
    keywords="network automation http requests async queue monitoring",
    project_urls={
        "Bug Reports": "https://github.com/your-org/network-automation-sender/issues",
        "Source": "https://github.com/your-org/network-automation-sender",
        "Documentation": "https://network-automation-sender.readthedocs.io/",
    },
)