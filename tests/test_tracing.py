from unittest.mock import MagicMock, patch

import pytest

from analytics_copilot.observability.tracing import flush_langfuse, get_langfuse


@pytest.fixture(autouse=True)
def clear_langfuse_cache() -> None:
    get_langfuse.cache_clear()
    yield
    get_langfuse.cache_clear()


def test_get_langfuse_returns_none_when_keys_missing() -> None:
    with patch("analytics_copilot.observability.tracing.get_settings") as mock_settings:
        settings = MagicMock()
        settings.langfuse_public_key = None
        settings.langfuse_secret_key = None
        mock_settings.return_value = settings

        result = get_langfuse()

    assert result is None


def test_get_langfuse_returns_none_when_only_public_key_set() -> None:
    with patch("analytics_copilot.observability.tracing.get_settings") as mock_settings:
        settings = MagicMock()
        settings.langfuse_public_key = MagicMock()
        settings.langfuse_secret_key = None
        mock_settings.return_value = settings

        result = get_langfuse()

    assert result is None


def test_get_langfuse_returns_client_when_keys_set() -> None:
    with (
        patch("analytics_copilot.observability.tracing.get_settings") as mock_settings,
        patch("analytics_copilot.observability.tracing.Langfuse") as mock_cls,
    ):
        settings = MagicMock()
        settings.langfuse_public_key = MagicMock()
        settings.langfuse_public_key.get_secret_value.return_value = "pk-test"
        settings.langfuse_secret_key = MagicMock()
        settings.langfuse_secret_key.get_secret_value.return_value = "sk-test"
        settings.langfuse_host = "https://cloud.langfuse.com"
        mock_settings.return_value = settings

        mock_client = MagicMock()
        mock_cls.return_value = mock_client

        result = get_langfuse()

    assert result is mock_client
    mock_cls.assert_called_once_with()


def test_get_langfuse_is_cached() -> None:
    with (
        patch("analytics_copilot.observability.tracing.get_settings") as mock_settings,
        patch("analytics_copilot.observability.tracing.Langfuse") as mock_cls,
    ):
        settings = MagicMock()
        settings.langfuse_public_key = MagicMock()
        settings.langfuse_public_key.get_secret_value.return_value = "pk"
        settings.langfuse_secret_key = MagicMock()
        settings.langfuse_secret_key.get_secret_value.return_value = "sk"
        settings.langfuse_host = "https://cloud.langfuse.com"
        mock_settings.return_value = settings
        mock_cls.return_value = MagicMock()

        get_langfuse()
        get_langfuse()

    mock_cls.assert_called_once()


def test_flush_langfuse_calls_flush_when_client_exists() -> None:
    mock_client = MagicMock()
    with patch(
        "analytics_copilot.observability.tracing.get_langfuse", return_value=mock_client
    ):
        flush_langfuse()

    mock_client.flush.assert_called_once()


def test_flush_langfuse_is_noop_when_client_is_none() -> None:
    with patch(
        "analytics_copilot.observability.tracing.get_langfuse", return_value=None
    ):
        flush_langfuse()  # should not raise
