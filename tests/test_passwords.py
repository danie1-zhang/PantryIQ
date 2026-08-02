from src.security.passwords import hash_password, verify_password


def test_password_hashing_and_verification() -> None:
    password = "a sufficiently long password"
    first = hash_password(password)
    second = hash_password(password)

    assert first != password
    assert first != second
    assert verify_password(password, first)
    assert not verify_password("the wrong password", first)
