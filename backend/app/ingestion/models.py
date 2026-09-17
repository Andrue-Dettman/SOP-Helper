"""Internal source types. G1 owns public API schemas."""

from dataclasses import dataclass
from hashlib import sha256
from urllib.parse import quote


class SourceValidationError(ValueError):
    """A corpus must be corrected before it can be published."""


@dataclass(frozen=True)
class Block:
    block_id: str
    kind: str
    text: str
    section_id: str
    start: int
    end: int
    applies_to: tuple[str, ...] = ()
    order: int | None = None


@dataclass(frozen=True)
class Section:
    section_id: str
    title: str
    text: str
    start: int
    end: int


@dataclass(frozen=True)
class Document:
    document_id: str
    version: str
    title: str
    effective_date: str
    procedure_key: str
    scope: str
    supersedes: tuple[str, ...]
    source: str
    checksum: str
    sections: tuple[Section, ...]
    blocks: tuple[Block, ...]

    @property
    def key(self) -> tuple[str, str]:
        return self.document_id, self.version


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    document_id: str
    version: str
    section_id: str
    title: str
    text: str


def source_uri(document_id: str, version: str, section_id: str) -> str:
    return (
        f"/api/sops/{quote(document_id, safe='')}/sections/"
        f"{quote(section_id, safe='')}?version={quote(version, safe='')}"
    )


def stable_id(*values: str) -> str:
    # Length prefixes avoid ambiguous concatenations without assuming safe separators.
    value = ''.join(f'{len(item)}:{item}' for item in values)
    return sha256(value.encode('utf-8')).hexdigest()
