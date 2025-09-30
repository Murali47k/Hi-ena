from setuptools import setup, find_packages

setup(
    name="Hi-ena",
    version="1.0.0",
    packages=find_packages(),
    include_package_data=True,  
    install_requires=[
        "PyQt5",
    ],
    entry_points={
        "console_scripts": [
            "Hi-ena=hi_ena:main",
        ]
    },
)
