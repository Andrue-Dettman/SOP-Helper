from pathlib import Path
import shutil

import pytest

from backend.app.ingestion.catalog import MemoryCatalog, ingest

CORPUS = Path(__file__).resolve().parents[2] / 'data' / 'sops'


@pytest.fixture
def corpus(tmp_path):
    target = tmp_path / 'sops'
    shutil.copytree(CORPUS, target)
    return target


@pytest.fixture
def catalog():
    result = MemoryCatalog()
    ingest(CORPUS, result)
    return result
