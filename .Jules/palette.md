# Palette's Journal

## 2026-03-30 - Gradio Textbox Enter Submission & Hidden Label Accessibility
**Learning:** In Gradio interfaces, textboxes with `show_label=False` omit accessible names for screen readers unless an explicit `label` attribute is provided. Additionally, text input fields for search/read operations often lack `.submit()` handlers, frustrating keyboard users who expect pressing Enter to trigger the search.
**Action:** Always provide explicit `label="..."` strings even when `show_label=False`, and ensure both `.click()` and `.submit()` event triggers are wired for search and input textboxes.
