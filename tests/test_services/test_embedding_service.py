"""Tests for the embedding service."""

import pytest


class TestCosine:
    """Pure unit tests for the _cosine similarity helper."""

    def test_identical_vectors_return_one(self):
        from app.services.embedding_service import _cosine

        v = [1.0, 0.0, 1.0]
        assert _cosine(v, v) == pytest.approx(1.0)

    def test_orthogonal_vectors_return_zero(self):
        from app.services.embedding_service import _cosine

        assert _cosine([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)

    def test_zero_vector_returns_zero_no_division_error(self):
        from app.services.embedding_service import _cosine

        assert _cosine([0.0, 0.0], [1.0, 0.5]) == 0.0

    def test_partial_similarity_is_between_zero_and_one(self):
        from app.services.embedding_service import _cosine

        score = _cosine([1.0, 1.0], [1.0, 0.0])
        assert 0.0 < score < 1.0


class TestEmbedTexts:
    @pytest.mark.asyncio
    async def test_no_api_key_returns_none(self):
        from unittest.mock import MagicMock, patch
        from app.services.embedding_service import embed_texts

        mock_settings = MagicMock()
        mock_settings.xai_api_key = ""
        with patch("app.config.settings", mock_settings):
            result = await embed_texts(["hello world"])

        assert result is None

    @pytest.mark.asyncio
    async def test_api_error_returns_none(self):
        from unittest.mock import AsyncMock, MagicMock, patch
        from app.services.embedding_service import embed_texts

        mock_settings = MagicMock()
        mock_settings.xai_api_key = "fake-key"
        mock_settings.xai_base_url = "https://api.x.ai/v1"
        mock_settings.embedding_model = "text-embedding-3-small"

        mock_openai = MagicMock()
        mock_openai.embeddings = MagicMock()
        mock_openai.embeddings.create = AsyncMock(side_effect=Exception("API error"))

        with patch("app.config.settings", mock_settings):
            with patch("openai.AsyncOpenAI", return_value=mock_openai):
                result = await embed_texts(["hello"])

        assert result is None


class TestSemanticRank:
    @pytest.mark.asyncio
    async def test_empty_texts_returns_empty_list(self):
        from app.services.embedding_service import semantic_rank

        result = await semantic_rank("query", [])
        assert result == []

    @pytest.mark.asyncio
    async def test_no_api_key_returns_none(self):
        from unittest.mock import MagicMock, patch
        from app.services.embedding_service import semantic_rank

        mock_settings = MagicMock()
        mock_settings.xai_api_key = ""
        with patch("app.config.settings", mock_settings):
            result = await semantic_rank("ransomware", ["malware alert"])

        assert result is None
