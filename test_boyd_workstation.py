"""Tests for Boyd Workstation UI construction, UX/a11y, advanced LLM parameters, styles, and outbox viewer."""

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


def test_ollama_chat_custom_parameters():
    """Test passing custom temperature and num_ctx options to Ollama chat payload."""
    mock_resp = MagicMock()
    mock_resp.__enter__.return_value = [b'{"message": {"content": "Hello!"}, "done": true}']

    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
        results = list(boyd_workstation.ollama_chat(
            model="qwen3:4b",
            system="Test System Prompt",
            messages=[{"role": "user", "content": "Hi"}],
            stream=True,
            temperature=0.2,
            num_ctx=8192,
        ))
        assert "Hello!" in results
        # Inspect URL request payload
        req = mock_urlopen.call_args[0][0]
        payload = json.loads(req.data.decode("utf-8"))
        assert payload["options"]["temperature"] == 0.2
        assert payload["options"]["num_ctx"] == 8192


def test_brain_enhance_style_and_negatives():
    """Test prompt brain generator with visual style modifier and negative templates."""
    with patch("boyd_workstation.ollama_chat", return_value=iter(["Expanded Cyberpunk Prompt"])) as mock_chat:
        results = list(boyd_workstation.brain_enhance(
            short="cyberpunk girl",
            model="qwen3:4b",
            with_negatives=True,
            style_key="🏙️ Cyberpunk Neon",
            neg_template="Heavy Clean (No Artifacts)",
            temp=0.8,
        ))
        assert "Expanded Cyberpunk Prompt" in results
        # Check that style modifier was appended to prompt
        user_arg = mock_chat.call_args[0][2][0]["content"]
        assert "cyberpunk girl, cyberpunk style, glowing neon lights" in user_arg


def test_export_and_outbox_viewer(tmp_path):
    """Test exporting session history and managing outbox files via outbox viewer helpers."""
    with patch("boyd_workstation.EXPORT_DIR", tmp_path):
        history = [
            {"role": "user", "content": "How do I test python code?"},
            {"role": "assistant", "content": "Use pytest!"},
        ]
        res_session = boyd_workstation.export_session_to_outbox(history, "chat")
        assert "Exported session" in res_session

        files = boyd_workstation.list_outbox_files()
        assert len(files) == 1
        filename = files[0]

        content = boyd_workstation.read_outbox_file(filename)
        assert "How do I test python code?" in content
        assert "Use pytest!" in content

        msg, dropdown = boyd_workstation.delete_outbox_file(filename)
        assert "Deleted" in msg
        assert len(boyd_workstation.list_outbox_files()) == 0
