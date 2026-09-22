"""Tests for Boyd Workstation UI construction and UX/a11y enhancements."""

import gradio as gr
import boyd_workstation


def test_build_app_structure_and_accessibility():
    """Verify that build() constructs Gradio Blocks with proper labels and CSS."""
    demo = boyd_workstation.build()
    assert isinstance(demo, gr.Blocks)
    assert "#link-bar a:focus-visible" in boyd_workstation.CSS


def test_textbox_labels_and_events():
    """Verify textboxes have explicit accessible labels and submit event triggers."""
    demo = boyd_workstation.build()

    # Inspect components inside the Blocks demo
    textboxes = [c for c in demo.blocks.values() if isinstance(c, gr.Textbox)]
    labels = [t.label for t in textboxes]

    # Verify accessibility labels on textboxes
    assert "Chat message" in labels
    assert "NPC message" in labels
    assert "Code snippet or prompt" in labels
    assert "Knowledge search query" in labels
    assert "Skill hunt query" in labels

    # Verify submit functions are attached to search/read textboxes
    listeners = list(demo.fns.values())
    targets = [target for fn in listeners for target in fn.targets]

    kq_box = next(t for t in textboxes if t.label == "Knowledge search query")
    vault_box = next(t for t in textboxes if t.label == "Vault relative path")
    skill_ref = next(t for t in textboxes if t.label == "Ref")

    # kq_box, vault_box, and skill_ref should all have ('submit') listeners attached
    assert (kq_box._id, "submit") in targets
    assert (vault_box._id, "submit") in targets
    assert (skill_ref._id, "submit") in targets
