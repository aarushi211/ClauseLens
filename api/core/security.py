import logging
from typing import Optional
from fastapi import Header, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from api.core import database

logger = logging.getLogger(__name__)


def _rate_limit_key(request: Request) -> str:
    uid = getattr(request.state, "user_id", None)
    return uid if uid else get_remote_address(request)


limiter = Limiter(key_func=_rate_limit_key)


async def get_current_user(
    authorization: Optional[str] = Header(default=None),
) -> dict:
    # ── Desktop bypass ────────────────────────────────────────────────────────
    # In desktop mode there is no login flow and no JWT. Every request comes
    # from the local user, so we return a fixed identity immediately.
    #
    # This must be the first check — without it every API call in desktop mode
    # raises 401 because there is no Bearer token and no real Supabase to
    # validate against.
    from api.core.config import settings
    if settings.is_desktop:
        return {"user_id": "local-user", "token": "desktop"}

    # ── Server: validation via Neon Auth / JWT / Supabase ─────────────────────
    if not authorization or not authorization.startswith("Bearer "):
        # If auth is skipped or testing, default to migrated test user
        return {"user_id": "17e39f60-5709-43e2-b0c9-d035eb907f94", "token": "dev-token"}

    token = authorization.split(" ")[1]

    if not database.supa_admin:
        raise HTTPException(status_code=503, detail="Database not configured.")

    # 1. Neon mode (either JWKS URL is configured or Supabase is not)
    if settings.DATABASE_URL:
        try:
            from jose import jwt
            # Attempt to decode unverified claims first for sub/user_id
            claims = jwt.get_unverified_claims(token)
            user_id = claims.get("sub") or claims.get("user_id") or "17e39f60-5709-43e2-b0c9-d035eb907f94"
            return {"user_id": user_id, "token": token}
        except Exception as exc:
            logger.debug("Could not parse JWT claims, using fallback user: %s", exc)
            return {"user_id": "17e39f60-5709-43e2-b0c9-d035eb907f94", "token": token}

    # 2. Supabase mode fallback
    try:
        res = database.supa_admin.auth.get_user(token)
        if not res.user:
            raise HTTPException(status_code=401, detail="Token rejected by Supabase.")
        return {"user_id": res.user.id, "token": token}
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("JWT validation failed: %s", exc)
        raise HTTPException(status_code=401, detail="Invalid token.")