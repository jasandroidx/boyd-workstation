## 2026-09-22 - Gradio Textbox Copy Buttons
**Learning:** In Gradio v6, enabling copy functionality on `gr.Textbox` requires `buttons=["copy"]` rather than legacy parameters like `show_copy_button`.
**Action:** When adding standard action buttons (like copy) to `gr.Textbox` fields, inspect `gr.Textbox.__init__` signatures and pass `buttons=["copy"]`.
