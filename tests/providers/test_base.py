"""Verify TTSProvider contract is enforceable."""

import pytest

from polyphon.providers.base import TTSProvider


def test_cannot_instantiate_abstract_provider() -> None:
    with pytest.raises(TypeError):
        TTSProvider()  # type: ignore[abstract]
