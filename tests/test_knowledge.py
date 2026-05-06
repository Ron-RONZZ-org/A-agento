"""Tests for A-agento knowledge commands."""

from __future__ import annotations


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
