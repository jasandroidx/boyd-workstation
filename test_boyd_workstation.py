"""Tests for Boyd Workstation UI construction and UX/a11y enhancements."""

import json
from unittest.mock import patch, MagicMock
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


def test_fetch_ollama_tags_success():
    """Test fetching model tags from simulated Ollama /api/tags endpoint."""
    mock_payload = json.dumps({
        "models": [
            {"name": "deepseek-coder:6.7b"},
            {"name": "mistral:7b"},
        ]
    }).encode("utf-8")

    mock_resp = MagicMock()
    mock_resp.read.return_value = mock_payload
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        tags = boyd_workstation.fetch_ollama_tags()
        assert "deepseek-coder:6.7b" in tags
        assert "mistral:7b" in tags
        # Should also include default models
        assert "qwen3:4b" in tags


def test_fetch_ollama_tags_fallback():
    """Test fallback to default models if Ollama /api/tags is unreachable."""
    with patch("urllib.request.urlopen", side_effect=Exception("Connection refused")):
        tags = boyd_workstation.fetch_ollama_tags()
        assert tags == boyd_workstation.DEFAULT_MODELS


def test_model_dropdown_choices_and_refresh():
    """Test generating dropdown choices with star on recommended model."""
    choices = boyd_workstation.model_dropdown_choices("chat", dynamic_models=["qwen3:4b", "custom-model:latest"])
    assert choices[0] == ("★ qwen3:4b — recommended", "qwen3:4b")
    assert ("custom-model:latest", "custom-model:latest") in choices

    dropdown = boyd_workstation.refresh_model_choices("code")
    assert isinstance(dropdown, gr.Dropdown)


def test_apply_preset():
    """Test applying quick prompt presets."""
    preset_dict = {"Test Preset": "Prefix text:\n\n"}
    # Blank text -> returns prefix
    assert boyd_workstation.apply_preset("", "Test Preset", preset_dict) == "Prefix text:\n\n"
    # Non-blank text -> prepends prefix
    assert boyd_workstation.apply_preset("user query", "Test Preset", preset_dict) == "Prefix text:\n\n\nuser query"
    # Invalid key -> returns current text unchanged
    assert boyd_workstation.apply_preset("user query", "Invalid", preset_dict) == "user query"


def test_export_session_and_text_to_outbox(tmp_path):
    """Test exporting session history and text content to the outbox directory."""
    with patch("boyd_workstation.EXPORT_DIR", tmp_path):
        history = [
            {"role": "user", "content": "How do I reverse a list in Python?"},
            {"role": "assistant", "content": "Use `list.reverse()` or `list[::-1]`."},
        ]
        res_session = boyd_workstation.export_session_to_outbox(history, "code")
        assert "Exported session" in res_session

        files = list(tmp_path.glob("SESSION-CODE-*.md"))
        assert len(files) == 1
        content = files[0].read_text()
        assert "How do I reverse a list in Python?" in content
        assert "Use `list.reverse()` or `list[::-1]`." in content

        res_text = boyd_workstation.export_text_to_outbox("Sample expanded prompt content", "brain")
        assert "Exported content" in res_text

        text_files = list(tmp_path.glob("EXPORT-BRAIN-*.md"))
        assert len(text_files) == 1
        assert "Sample expanded prompt content" in text_files[0].read_text()
