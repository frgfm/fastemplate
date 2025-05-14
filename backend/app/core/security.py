# Copyright (C) 2025, François-Guillaume Fernandez.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.


import bcrypt

__all__ = ["hash_password", "verify_password"]


def hash_password(password: str) -> str:
    # Generate a salt and hash the password
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode("utf-8"), salt)
    # Decode the hashed password to a string before returning
    return hashed_password.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    # Encode both the plain password and the hashed password
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
