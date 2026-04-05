from setuptools import find_packages, setup

setup(
    name="hbctool",
    version="0.1.5",
    description="A command-line interface for disassembling and assembling the Hermes Bytecode.",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="baba01hacker",
    license="MIT",
    url="https://github.com/Baba01hacker666/HBC-Tool",
    project_urls={
        "Homepage": "https://github.com/Baba01hacker666/HBC-Tool",
        "Repository": "https://github.com/Baba01hacker666/HBC-Tool",
        "Documentation": "https://github.com/Baba01hacker666/HBC-Tool",
    },
    packages=find_packages(),
    include_package_data=True,
    install_requires=["docopt>=0.6.2,<0.7.0"],
    entry_points={"console_scripts": ["hbctool=hbctool:main"]},
    python_requires=">=3.6",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Natural Language :: English",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
)
