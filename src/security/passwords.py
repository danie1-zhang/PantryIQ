from pwdlib import PasswordHash

MIN_PASSWORD_LENGTH = 12
MAX_PASSWORD_LENGTH = 1024

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Hash a validated password with Argon2."""

    if not MIN_PASSWORD_LENGTH <= len(password) <= MAX_PASSWORD_LENGTH:
        raise ValueError(
            f"Password must be between {MIN_PASSWORD_LENGTH} and {MAX_PASSWORD_LENGTH} characters"
        )
    return password_hash.hash(password)


def verify_password(password: str, encoded_hash: str) -> bool:
    """Return false for an incorrect password or an invalid stored hash."""

    try:
        return password_hash.verify(password, encoded_hash)
    except (ValueError, TypeError):
        return False
