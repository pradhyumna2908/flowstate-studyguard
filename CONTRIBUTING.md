# Contributing to FlowState StudyGuard 🧠

Thank you for your interest in contributing to FlowState StudyGuard! We are building a privacy-first, edge-computing multi-modal behavioral monitor that solves the "Inattentive Screen Viewing" problem in modern digital learning.

---

## 📜 Code of Conduct

We are committed to providing a welcoming, inclusive, and harassment-free environment for everyone regardless of identity or background.

---

## 🛠️ Development Setup

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/pradhyumna2908/flowstate-studyguard.git
   cd flowstate-studyguard
   ```

2. **Create and Activate Virtual Environment**:
   ```bash
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On Linux/macOS:
   source venv/bin/activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install -e .
   ```

4. **Verify Test Suite**:
   ```bash
   pytest
   ```

---

## 🧪 Testing Guidelines

* Every new feature or bugfix **must** be accompanied by unit tests in the `tests/` directory.
* Assertions must cover both typical flows and boundary/edge-case conditions (e.g. empty camera frames, missing face landmarks, corrupted network strings).
* Run the benchmark suite to ensure no inference latency regressions:
  ```bash
  python benchmark.py --verify-sla
  ```

---

## 📐 Coding Standards & Conventions

* **PEP 8 Compliance**: Follow standard Python conventions. Keep lines under 120 characters where practical.
* **Type Annotations**: Use Python type hints (`Optional`, `List`, `Dict`, `Tuple`) on all public function interfaces.
* **Edge-First Architecture**: All biometric computations and window classifications must execute 100% locally with zero external network dependencies.
* **Accessibility**: UI additions in Streamlit must provide WCAG-compliant color contrast ratios and keyboard navigation support.

---

## 🚀 Pull Request Workflow

1. Fork the repository and create your feature branch:
   ```bash
   git checkout -b feature/amazing-feature
   ```
2. Commit your changes with clear, descriptive messages:
   ```bash
   git commit -m "feat(biometrics): add micro-saccadic velocity vector calculation"
   ```
3. Push to your branch:
   ```bash
   git push origin feature/amazing-feature
   ```
4. Open a Pull Request targeting the `main` branch.
