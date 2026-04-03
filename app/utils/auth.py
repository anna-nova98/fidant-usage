from fastapi import Header, HTTPException


def get_current_user_id(authorization: str = Header(...)) -> int:
    """
    FastAPI dependency that extracts and validates the authenticated user ID.

    Expects the Authorization header in the format: "Bearer <user_id>"

    NOTE: This is a simplified demo implementation that treats the raw user ID
    as the token. In production, replace this with proper JWT verification
    (e.g., using python-jose) — decode the token, verify the signature against
    a secret key, and extract the subject claim.

    Raises:
        HTTPException 401: If the header is missing, malformed, or the token
                           cannot be parsed as a valid integer user ID.
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail={"error": "unauthorized", "message": "Missing or invalid Authorization header"},
        )

    token = authorization.removeprefix("Bearer ").strip()

    try:
        user_id = int(token)
    except ValueError:
        raise HTTPException(
            status_code=401,
            detail={"error": "unauthorized", "message": "Invalid token"},
        )

    return user_id
