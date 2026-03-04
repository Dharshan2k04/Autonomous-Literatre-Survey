import pytest
from app.core.security import hash_password, verify_password, create_access_token, decode_token


class TestPasswordHashing:
    def test_hash_and_verify(self):
        password = "MySecurePassword123!"
        hashed = hash_password(password)
        assert hashed != password
        assert verify_password(password, hashed) is True

    def test_wrong_password(self):
        hashed = hash_password("correct")
        assert verify_password("wrong", hashed) is False


class TestJWT:
    def test_create_and_decode_token(self):
        token = create_access_token(data={"sub": "user-123"})
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "user-123"

    def test_invalid_token(self):
        payload = decode_token("invalid.token.here")
        assert payload is None
