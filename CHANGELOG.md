# Changelog 📋

All notable changes to the FlowState StudyGuard project are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.0.0] - 2026-09-30

### Added
- **Multi-Modal Decision Fusion**: Resolves "Inattentive Screen Viewing" via 3 pillars: Biometric Glare (RMSSD), Eye Dynamics (EAR + Saccades), and Peripheral Activity (Keyboard/Mouse dynamics).
- **Direct Message Dispatch Engine**: Dispatches notifications directly to parent mobile numbers via Twilio SMS/WhatsApp, CallMeBot, Fast2SMS, or real-time local network state bus.
- **Parent Mobile Portal (`?view=parent`)**: Real-time Wi-Fi dashboard with QR code pairing and two-way encouragement nudges.
- **Automated Testing Suite (`tests/`)**: 46 comprehensive unit tests asserting tensor shapes, biometrics, domain models, and boundary conditions.
- **Empirical Efficiency Benchmarking (`benchmark.py`)**: Sub-2ms inference latency profiling across batch sizes with JSON reporting.
- **Formally Declared Problem Ontology (`domain_models.py`)**: 57 declared domain concepts implemented as typed classes and enums.
- **Cloud Compatibility**: Added `packages.txt`, `opencv-python-headless`, and `SimulatedWebcam` fallback for seamless Streamlit Cloud deployments.
- **UN SDG 9 Mapping**: Formal socio-technical documentation aligned with UN SDG Target 9.4 (resilient retrofitting) and Targets 9.c / 9.5.

### Changed
- Minimalist, distraction-free UI with expandable diagnostics to prevent visual clutter and ADHD overstimulation.
- Native Windows ctypes hooks (`GetForegroundWindow`, `ShowWindow`, `PostMessageW`) now include cross-platform Linux fallback guards.

### Security
- Zero cloud video transmission: 100% edge processing on local CPU.
- Clean credential hygiene: zero exposed API keys or tokens in repository.
