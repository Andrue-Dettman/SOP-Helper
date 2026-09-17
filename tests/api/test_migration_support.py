from types import SimpleNamespace

import pytest
from sqlalchemy import MetaData

from app.api import migration_support
from app.database import Base


def test_shared_environment_includes_both_domain_metadata(monkeypatch):
    retrieval_metadata = MetaData()
    imported = []
    def import_domain(name):
        imported.append(name)
        return SimpleNamespace(metadata=retrieval_metadata)
    monkeypatch.setattr(migration_support, "import_module", import_domain)
    metadata, missing = migration_support.collect_metadata()
    assert imported == ["app.inventory.models", "app.ingestion.schema"]
    assert metadata == [Base.metadata, retrieval_metadata] and not missing
    migration_support.revision_guard(missing)(None, None, [])


def test_missing_domain_allows_existing_upgrades_but_blocks_autogeneration(monkeypatch):
    def missing_domain(name):
        raise ModuleNotFoundError(name=name.rsplit(".", 1)[0])
    monkeypatch.setattr(migration_support, "import_module", missing_domain)
    metadata, missing = migration_support.collect_metadata()
    assert metadata == [Base.metadata]
    assert missing == ["app.inventory.models", "app.ingestion.schema"]
    with pytest.raises(RuntimeError, match="Integrate all domain models"):
        migration_support.revision_guard(missing)(None, None, [])


def test_broken_transitive_dependency_is_not_silently_ignored(monkeypatch):
    def broken_dependency(name):
        raise ModuleNotFoundError(name="a_required_domain_dependency")
    monkeypatch.setattr(migration_support, "import_module", broken_dependency)
    with pytest.raises(ModuleNotFoundError) as error:
        migration_support.collect_metadata()
    assert error.value.name == "a_required_domain_dependency"
