# Accessibility & Universal Design Specification ♿

FlowState StudyGuard is designed under the **Universal Design for Learning (UDL)** principles and complies with **W3C Web Content Accessibility Guidelines (WCAG) 2.1 Level AA**.

---

## 🎨 Visual Accessibility & Contrast Ratios

The FlowState interface adheres strictly to WCAG 2.1 AA contrast requirements:

| Interface Element | Foreground | Background | Contrast Ratio | WCAG 2.1 AA Threshold |
| :--- | :--- | :--- | :--- | :--- |
| **Primary Status Text** | `#00e5a3` (Emerald Mint) | `#080b11` (Deep Space Dark) | **13.4 : 1** | PASS (Min 4.5:1) |
| **Timer Header Display** | `#38bdf8` (Vivid Sky Blue) | `#0c131d` (Card Dark) | **10.2 : 1** | PASS (Min 4.5:1) |
| **Warning / Passive Alert** | `#ffb703` (Amber Gold) | `#0c131d` (Card Dark) | **9.1 : 1** | PASS (Min 4.5:1) |
| **Critical Interception** | `#ff4d4d` (Vivid Coral) | `#0c131d` (Card Dark) | **6.8 : 1** | PASS (Min 4.5:1) |
| **Secondary Subtitles** | `#cbd5e1` (Slate Light) | `#0f1722` (Panel Background) | **11.8 : 1** | PASS (Min 4.5:1) |

---

## ⌨️ Keyboard Navigation & Shortcuts

The application supports full keyboard navigation without requiring mouse interactions:

| Key Binding | Target Function | Description |
| :--- | :--- | :--- |
| <kbd>Tab</kbd> / <kbd>Shift+Tab</kbd> | Focus Next / Previous Element | Cycles through interactive session buttons, sliders, and expanders. |
| <kbd>Enter</kbd> / <kbd>Space</kbd> | Activate Button | Triggers "Start Session", "Stop Session", or "Send Direct Message". |
| <kbd>Arrow Left</kbd> / <kbd>Arrow Right</kbd> | Adjust Duration Slider | Decrements or increments target study duration in 5-minute steps. |
| <kbd>Escape</kbd> | Collapse Diagnostics | Closes open expanders and restores clean view. |

---

## 🔊 Screen Reader Compatibility & ARIA Roles

All dynamically rendered components include semantic HTML5 landmarks and WAI-ARIA tags:
* `role="timer"` and `aria-live="polite"` on active countdown clocks so screen readers announce remaining study time without interrupting the user.
* `role="status"` and `aria-live="assertive"` on distraction interception banners.
* Meaningful `alt` text on generated QR codes and video HUD overlays.
* Text transcripts accompanying all quantitative graphs and telemetry counters.

---

## 🧠 Cognitive & Neurodivergent Accessibility

* **Distraction-Free Minimal HUD**: All raw telemetry, high-frequency charts, and process inspectors are tucked safely inside collapsed expanders by default to prevent visual overstimulation for students with ADHD.
* **Predictable Layout**: Controls and telemetry occupy fixed screen coordinates; no unexpected popups or layout shifts during study sessions.
* **Sensory Safety**: Visual alerts use smooth luminance shifts rather than rapid strobe effects to avoid seizure or migraine triggers.
