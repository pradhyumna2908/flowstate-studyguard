from setuptools import setup, find_packages

setup(
    name="flowstate-studyguard",
    version="2.0.0",
    description="Multi-Modal AI StudyGuard detecting inattentive screen viewing through biometric signals and active window monitoring.",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="VisionFlow Team",
    packages=find_packages(),
    py_modules=["study_guard", "domain_models", "benchmark"],
    install_requires=[
        "streamlit>=1.38.0",
        "mediapipe>=1.0.1",
        "opencv-python>=4.8.0",
        "numpy>=1.24.0",
        "qrcode>=8.0",
        "pytest>=8.0.0",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Microsoft :: Windows",
    ],
    python_requires=">=3.10",
)
