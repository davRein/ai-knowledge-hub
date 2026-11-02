from argon2 import PasswordHasher, Type
from argon2.exceptions import VerificationError

hasher = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1, type=Type.ID)
DUMMY_HASH = hasher.hash("timing-placeholder-not-an-account-password")


def verify_password(encoded: str, password: str) -> bool:
    try:
        return hasher.verify(encoded, password)
    except VerificationError:
        return False
