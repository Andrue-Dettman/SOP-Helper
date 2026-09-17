from pathlib import Path
import os
import shutil
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'backend'))
if os.environ.get('WAREHOUSE_G1_BACKEND'):
    sys.path.append(os.environ['WAREHOUSE_G1_BACKEND'])

from app.ingestion.catalog import MemoryCatalog, ingest

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
