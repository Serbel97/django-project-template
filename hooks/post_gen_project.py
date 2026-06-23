#!/usr/bin/env python
"""
Cookiecutter post-generation hook.

Runs in the generated project directory after rendering. It creates a ``.env``
from ``.env.example`` with a freshly generated ``SECRET_KEY`` so the project is
runnable immediately (every ``manage.py`` command requires ``SECRET_KEY``).
"""
import secrets
from pathlib import Path

# Avoid characters that are awkward in .env values: quotes, '#', '$', whitespace.
SECRET_KEY_CHARS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@%^&*(-_=+)"


def generate_secret_key(length: int = 50) -> str:
    return "".join(secrets.choice(SECRET_KEY_CHARS) for _ in range(length))


def main() -> None:
    example = Path(".env.example")
    env = Path(".env")

    if not example.exists() or env.exists():
        return

    content = example.read_text()
    # Replace the bare ``SECRET_KEY=`` line with a generated value.
    content = content.replace("SECRET_KEY=\n", f"SECRET_KEY={generate_secret_key()}\n", 1)
    env.write_text(content)

    print("Created .env with a generated SECRET_KEY.")
    print("Next: configure the PG* database variables in .env, then run `make migrations`.")


if __name__ == "__main__":
    main()
