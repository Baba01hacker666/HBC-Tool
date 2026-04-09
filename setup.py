from setuptools import Extension, find_packages, setup

packages = find_packages()


fastutil_extension = Extension(
    "hbctool._fastutil",
    sources=["hbctool/_fastutil.cpp"],
    language="c++",
    extra_compile_args=["-O3"],
)

bitcodec_extension = Extension(
    "hbctool._bitcodec",
    sources=["hbctool/_bitcodec.cpp"],
    language="c++",
    extra_compile_args=["-O3"],
)

hbc_package_data = {
    package: ["data/*.json", "raw/*"]
    for package in packages
    if package.startswith("hbctool.hbc.hbc")
}

setup(
    name="hbctool-cli",
    version="0.1.6",
    description="A command-line interface for disassembling and assembling the Hermes Bytecode.",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="baba01hacker",
    author_email="117832562+Baba01hacker666@users.noreply.github.com",
    license="MIT",
    license_files=["LICENSE"],
    url="https://github.com/Baba01hacker666/HBC-Tool",
    project_urls={
        "Homepage": "https://github.com/Baba01hacker666/HBC-Tool",
        "Repository": "https://github.com/Baba01hacker666/HBC-Tool",
        "Documentation": "https://github.com/Baba01hacker666/HBC-Tool",
    },
    packages=packages,
    package_data=hbc_package_data,
    include_package_data=True,
    keywords=["hbc", "hermes", "bytecode", "reverse", "hacking"],
    install_requires=["docopt>=0.6.2,<0.7.0"],
    entry_points={"console_scripts": ["hbctool=hbctool:main"]},
    python_requires=">=3.6",
    ext_modules=[fastutil_extension, bitcodec_extension],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Natural Language :: English",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
)
