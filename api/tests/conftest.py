from pathlib import Path

import pytest

from jwt_support import install_public_key


@pytest.fixture(autouse=True)
def configured_public_key(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    install_public_key(monkeypatch, tmp_path)
