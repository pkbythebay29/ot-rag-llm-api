from setuptools import setup, find_packages
from pathlib import Path 
ROOT = Path(__file__).resolve().parent
readme_path = ROOT / "README-Krionis-pipeline.md"
long_description = readme_path.read_text(encoding="utf-8")


with open("requirements.txt", encoding="utf-8") as f:
    install_requires = f.read().splitlines()


setup(
    name="krionis-pipeline",
    version="0.8.1",
    author="pkbythebay29",
    author_email="kannan@haztechrisk.org",
    description="Krionis Pipeline - multimodal RAG pipeline for low-compute, local, real-world deployment",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/pkbythebay29/ot-rag-llm-api",
    packages=find_packages(),
    include_package_data=True,
    install_requires=install_requires,
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            # Old CLI retained for compatibility
            "rag-cli = rag_llm_api_pipeline.cli.main:main",
            # New branded CLI
            "krionis-cli = rag_llm_api_pipeline.cli.main:main",
        ],
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    project_urls={
        "Homepage": "https://pypi.org/project/krionis-pipeline/",
        "Source": "https://github.com/pkbythebay29/ot-rag-llm-api",
    },
)
