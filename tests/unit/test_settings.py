from __future__ import annotations

import pytest
from pydantic import ValidationError

from mf_facts.settings import Settings


def test_config_loads():
    s = Settings.load()
    assert s.scope.amc
    assert 1 <= len(s.scope.schemes) <= 8
    assert s.app.max_answer_sentences == 3


def test_invalid_backend_rejected():
    s = Settings.load()
    raw = s.model_dump()
    raw["phases"]["vectorstore"]["backend"] = "pinecone"
    with pytest.raises(ValidationError):
        Settings.model_validate(raw)


def test_invalid_embedding_provider_rejected():
    s = Settings.load()
    raw = s.model_dump()
    raw["phases"]["embedding"]["provider"] = "my-own-model"
    with pytest.raises(ValidationError):
        Settings.model_validate(raw)
