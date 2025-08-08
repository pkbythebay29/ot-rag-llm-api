from setuptools import setup, find_packages

with open("README.md", encoding="utf-8") as f:
    long_description = f.read()

with open("requirements.txt", encoding="utf-8") as f:
    install_requires = f.read().splitlines()
    
with open("CHANGELOG.md", encoding="utf-8") as f:
    install_requires = f.read().splitlines()

setup(
    name="rag-llm-api-pipeline",
    version="0.4.0",
    author="pkbythebay29",
    author_email="kannan@haztechrisk.org",
    description="Multimodal RAG pipeline for low-compute, local, real-world deployment",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/pkbythebay29/ot-rag-llm-api",
    packages=find_packages(),
    include_package_data=True,
    install_requires=install_requires,
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "rag-cli = rag_llm_api_pipeline.cli.main:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
