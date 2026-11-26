# Accessibility & Inclusive Design

AeroShield is designed to be usable across assistive technologies, keyboard-only navigation, and low-vision users:

- **Semantic Landmarks & Skip Navigation (`app/static/index.html`):** Includes a keyboard-focusable `Skip to main content` link, `<header>`, `<main>`, `<aside>`, and `<section>` landmarks.
- **ARIA Live Regions:** Telemetry updates (`aria-live="polite"`), form validation errors (`role="alert"`, `aria-live="assertive"`), and chat responses announce dynamically to screen readers.
- **High Contrast & Large Text Controls:** Built-in `High Contrast` (`body.high-contrast`) and `A+ Text` (`body.large-text`) toggles in the top bar with synchronized `aria-pressed` state.
- **Reduced Motion Support (`app/static/styles.css`, `app/static/app.js`):** Respects `@media (prefers-reduced-motion: reduce)` by disabling the Aurora canvas animation, pulse animations, and CountUp transitions.
- **Keyboard Focus Indicators:** Clear `:focus-visible` outlines (`2px solid #38bdf8`) on all interactive buttons, sliders, tabs, and inputs.
