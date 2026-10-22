"""Google OAuth callback coverage (Chainlit native auth — no custom system).

The callback is registered only when the environment provides credentials
(`_google_oauth_configured`), so these tests exercise the mapping logic
directly and assert that the guard keeps the app bootable without them.
"""

from __future__ import annotations

import pytest

import ui.app as app


class TestOAuthCallbackMapping:
    @pytest.mark.asyncio
    async def test_google_profile_maps_to_session_user(self):
        user = await app._oauth_callback(
            "google",
            "token",
            {"email": "juan@ejemplo.es", "name": "Juan", "id": "42"},
            None,
            None,
        )
        assert user is not None
        assert user.identifier == "juan@ejemplo.es"
        assert user.display_name == "Juan"
        assert user.metadata.get("provider") == "google"

    @pytest.mark.asyncio
    async def test_falls_back_to_default_user_email(self):
        default = app.cl.User(identifier="fallback@ejemplo.es", display_name="F")
        user = await app._oauth_callback("google", "token", {}, default, None)
        assert user is not None
        assert user.identifier == "fallback@ejemplo.es"
        assert user.display_name == "F"

    @pytest.mark.asyncio
    async def test_unknown_provider_is_rejected(self):
        user = await app._oauth_callback(
            "github", "token", {"email": "x@ejemplo.es"}, None, None
        )
        assert user is None

    @pytest.mark.asyncio
    async def test_missing_email_is_rejected(self):
        user = await app._oauth_callback("google", "token", {"name": "X"}, None, None)
        assert user is None


class TestOAuthConfigurationGuard:
    def test_not_configured_without_credentials(self, monkeypatch):
        monkeypatch.delenv("OAUTH_GOOGLE_CLIENT_ID", raising=False)
        monkeypatch.delenv("OAUTH_GOOGLE_CLIENT_SECRET", raising=False)
        assert app._google_oauth_configured() is False

    def test_configured_with_both_variables(self, monkeypatch):
        monkeypatch.setenv("OAUTH_GOOGLE_CLIENT_ID", "id")
        monkeypatch.setenv("OAUTH_GOOGLE_CLIENT_SECRET", "secret")
        assert app._google_oauth_configured() is True

    def test_partially_configured_is_false(self, monkeypatch):
        monkeypatch.setenv("OAUTH_GOOGLE_CLIENT_ID", "id")
        monkeypatch.delenv("OAUTH_GOOGLE_CLIENT_SECRET", raising=False)
        assert app._google_oauth_configured() is False
