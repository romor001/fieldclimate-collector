from setuptools import setup, find_packages

setup(
    name="fieldclimate-collector",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "requests>=2.25.0",
        "pyyaml>=5.1",
        "sqlite-utils>=3.0",
        "python-dateutil>=2.8.1",
        "click>=7.1.2",
    ],
    entry_points={
        "console_scripts": [
            "fieldclimate-collector=fieldclimate.cli:main",
        ],
    },
    python_requires=">=3.8",
    author="Your Name",
    author_email="your.email@example.com",
    description="Collects weather data from Pessl's FieldClimate platform",
    keywords="weather, agriculture, data collection",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
)