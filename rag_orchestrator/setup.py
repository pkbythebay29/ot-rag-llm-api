from setuptools import setup, find_packages

with open("README.md", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="krionis-orchestrator",
    version="0.3.0",
    author="pkbythebay29",
    author_email="kannan@haztechrisk.org",
    description="Krionis Orchestrator — agentic batching and coordination on top of the Krionis Pipeline",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/pkbythebay29/ot-rag-llm-api",
    packages=find_packages(),
    include_package_data=True,
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    project_urls={
        "Homepage": "https://pypi.org/project/krionis-orchestrator/",
        "Source": "https://github.com/pkbythebay29/ot-rag-llm-api",
    },
    entry_points={
    "console_scripts": [
        # New CLI
        "krionis-orchestrator = rag_orchestrator.cli.main:main",
        # Optional: keep the python -m path as a thin wrapper if you want
        # "rag-orchestrator = rag_orchestrator.cli.main:main",
        ],
    }, 
)
