"""Tests for A-agento knowledge commands."""

from __future__ import annotations

from pathlib import Path

import pytest


class TestCleanEncOutput:
    """Tests for _clean_enc_output."""

    def test_clean_fences(self):
        """Test that code fences are stripped."""
        from A_agento.commands.knowledge import _clean_enc_output

        raw = '```enc\nterminologio.eo = "test"\ndifino.eo = "def"\n```'
        result = _clean_enc_output(raw)
        assert result.startswith('terminologio')
        assert '```' not in result

    def test_title_comment_stripped(self):
        """Test that # title comment is stripped (tolerated by parser, not desired)."""
        from A_agento.commands.knowledge import _clean_enc_output

        raw = '# Albert Einstein\nterminologio.eo = "Albert Einstein"'
        result = _clean_enc_output(raw)
        assert not result.startswith('#')
        assert result.startswith('terminologio')

    def test_clean_both(self):
        """Test fences stripped and # comment stripped."""
        from A_agento.commands.knowledge import _clean_enc_output

        raw = '```\n# Albert Einstein\nterminologio.eo = "test"\n```'
        result = _clean_enc_output(raw)
        assert '```' not in result
        assert not result.startswith('#')

    def test_preserves_section_headers(self):
        """Test that ## section headers are preserved."""
        from A_agento.commands.knowledge import _clean_enc_output

        raw = '# Title\ndifino.eo = """\n## section\n- point 1\n"""'
        result = _clean_enc_output(raw)
        assert '## section' in result
        assert 'difino.eo' in result


class TestResolveUniquePath:
    """Tests for _resolve_unique_path."""

    def test_no_conflict(self, tmp_path):
        """Path that doesn't exist is returned as-is."""
        from A_agento.commands.knowledge import _resolve_unique_path
        p = tmp_path / "test.enc"
        assert _resolve_unique_path(p) == p

    def test_appends_number(self, tmp_path):
        """Existing file gets .1 suffix."""
        from A_agento.commands.knowledge import _resolve_unique_path
        p = tmp_path / "test.enc"
        p.write_text("original")
        result = _resolve_unique_path(p)
        assert result == tmp_path / "test.1.enc"
        assert not result.exists()

    def test_increments_number(self, tmp_path):
        """Multiple conflicts increment .1 → .2."""
        from A_agento.commands.knowledge import _resolve_unique_path
        p = tmp_path / "test.enc"
        p.write_text("v1")
        (tmp_path / "test.1.enc").write_text("v2")
        result = _resolve_unique_path(p)
        assert result == tmp_path / "test.2.enc"

    def test_preserves_extension(self, tmp_path):
        """Extension stays .txt, number goes before it."""
        from A_agento.commands.knowledge import _resolve_unique_path
        p = tmp_path / "doc.txt"
        p.write_text("original")
        result = _resolve_unique_path(p)
        assert result.suffix == ".txt"
        assert result.stem == "doc.1"


class TestSaveToFile:
    """Tests for _save_to_file."""

    def test_saves_new_file(self, tmp_path):
        """File that doesn't exist is saved directly."""
        from A_agento.commands.knowledge import _save_to_file
        p = tmp_path / "out.enc"
        result = _save_to_file(p, "content")
        assert result == p
        assert p.read_text() == "content"

    def test_auto_renames_on_conflict(self, tmp_path):
        """Existing file triggers auto-rename to .1."""
        from A_agento.commands.knowledge import _save_to_file
        p = tmp_path / "out.enc"
        p.write_text("old")
        result = _save_to_file(p, "new content")
        assert result != p
        assert result == tmp_path / "out.1.enc"
        assert result.read_text() == "new content"
        # Original file is preserved
        assert p.read_text() == "old"


class TestReadLocalFile:
    """Tests for _read_local_file."""

    def test_read_utf8(self, tmp_path):
        """Read a normal UTF-8 file."""
        from A_agento.commands.knowledge import _read_local_file

        f = tmp_path / "test.txt"
        f.write_text("Hello, World!", encoding="utf-8")
        result = _read_local_file(f)
        assert result == "Hello, World!"

    def test_read_latin1_fallback(self, tmp_path):
        """Latin-1 file should fall back gracefully."""
        from A_agento.commands.knowledge import _read_local_file

        f = tmp_path / "latin.txt"
        f.write_bytes(b"Bonjour \xe9")  # é in latin-1
        result = _read_local_file(f)
        assert "Bonjour" in result

    def test_file_too_large(self, tmp_path):
        """File exceeding MAX_FILE_BYTES should raise."""
        from A_agento.commands.knowledge import _read_local_file, _MAX_FILE_BYTES

        f = tmp_path / "big.txt"
        # Write a file slightly larger than the limit
        big_data = b"x" * (_MAX_FILE_BYTES + 1)
        f.write_bytes(big_data)

        with pytest.raises(ValueError, match="large|granda|volumineux"):
            _read_local_file(f)

    def test_sensitive_path_warns(self, tmp_path, monkeypatch):
        """Reading a file inside a sensitive directory should warn."""
        from A_agento.commands.knowledge import _read_local_file

        warnings: list[str] = []

        def _capture_warning(msg):
            warnings.append(str(msg))

        monkeypatch.setattr(
            "A_agento.commands.knowledge.warning",
            _capture_warning,
        )

        # Create a file inside tmp_path/.ssh (simulating ~/.ssh)
        ssh_dir = tmp_path / ".ssh"
        ssh_dir.mkdir()
        f = ssh_dir / "config"
        f.write_text("not-real", encoding="utf-8")

        # Monkeypatch Path.home to return tmp_path so that
        # sensitive_parents includes tmp_path/.ssh
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        _read_local_file(f)

        # Should have warned about sensitive path
        assert any("sensitive" in w.lower() for w in warnings)

    def test_nonexistent_file(self):
        """Non-existent file should raise."""
        from A_agento.commands.knowledge import _read_local_file

        from pathlib import Path
        with pytest.raises((ValueError, OSError)):
            _read_local_file(Path("/nonexistent/path/file.txt"))
