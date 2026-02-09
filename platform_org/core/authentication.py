import os
import jwt
from jwt import PyJWKClient
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import authentication, exceptions

User = get_user_model()

def _get_setting(name: str, default: str = "") -> str:
    return getattr(settings, name, os.getenv(name, default)) or os.getenv(name, default) or default

class EntraIDAuthentication(authentication.BaseAuthentication):
    """Production-grade Entra ID (Azure AD) bearer token validation.
    - verifies signature (JWKS)
    - verifies issuer (ENTRA_ALLOWED_ISSUER) when set
    - verifies audience (ENTRA_CLIENT_ID) when set
    Attaches decoded claims to request.entra_claims for tenant resolution.
    """

    def authenticate(self, request):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return None

        token = auth.split(" ", 1)[1].strip()
        if token.count(".") != 2:
            return None

        try:
            unverified = jwt.decode(token, options={"verify_signature": False})
        except Exception:
            return None

        iss = unverified.get("iss", "")
        if "login.microsoftonline.com" not in iss and "sts.windows.net" not in iss:
            return None

        allowed_issuer = _get_setting("ENTRA_ALLOWED_ISSUER", "")
        client_id = _get_setting("ENTRA_CLIENT_ID", "")
        verify_aud = bool(client_id)

        # Determine JWKS endpoint
        if iss.endswith("/v2.0"):
            jwks_url = iss.rstrip("/") + "/discovery/v2.0/keys"
        else:
            parts = iss.rstrip("/").split("/")
            tenant_id = parts[-1] if parts else "common"
            jwks_url = f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys"

        try:
            jwk_client = PyJWKClient(jwks_url)
            signing_key = jwk_client.get_signing_key_from_jwt(token)

            options = {"verify_aud": verify_aud}
            kwargs = {}
            if verify_aud:
                kwargs["audience"] = client_id

            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                options=options,
                **kwargs
            )
        except Exception as e:
            raise exceptions.AuthenticationFailed(f"Entra token invalid: {e}")

        if allowed_issuer and payload.get("iss") != allowed_issuer:
            raise exceptions.AuthenticationFailed("Entra token issuer not allowed")

        username = payload.get("preferred_username") or payload.get("upn") or payload.get("email")
        if not username:
            raise exceptions.AuthenticationFailed("Entra token missing preferred_username/upn/email")

        user, _ = User.objects.get_or_create(username=username, defaults={"email": payload.get("email","")})
        request.entra_claims = payload
        return (user, None)
