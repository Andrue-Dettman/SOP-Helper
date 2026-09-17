"""Load domain-owned metadata without hiding missing transitive dependencies."""
from importlib import import_module

from app.database import Base


def collect_metadata():
    metadata, missing = [Base.metadata], []
    for name in ("app.inventory.models", "app.ingestion.schema"):
        try:
            module = import_module(name)
        except ModuleNotFoundError as exc:
            if exc.name != name and not name.startswith((exc.name or "") + "."):
                raise
            missing.append(name)
            continue
        # C1 imports register tables on Base; G2 deliberately owns separate metadata.
        if name == "app.ingestion.schema":
            metadata.append(module.metadata)
    return metadata, missing


def revision_guard(missing):
    def guard(context, revision, directives):
        if missing:
            raise RuntimeError("Integrate all domain models before generating migrations: " + ", ".join(missing))
    return guard
