"""Parse the deliberately narrow SOP authoring format using CommonMark tokens.

Source offsets refer to the original decoded UTF-8 text, including its line endings.
Markdown is never rendered or executed by ingestion.
"""

import json
import re
from datetime import date
from hashlib import sha256

from markdown_it import MarkdownIt

from .models import Block, Chunk, Document, Section, SourceValidationError, stable_id

CHUNKER_VERSION = 'section-v1'
MAX_SOURCE_BYTES = 100_000
MAX_SECTION_CHARS = 12_000
_ID = re.compile(r'[a-z0-9][a-z0-9-]{0,79}\Z')
_HEADING = re.compile(r'(.+?) \{#([a-z0-9-]+)\}\Z')
_BLOCK = re.compile(
    r'(?:(?P<number>[1-9][0-9]*)\. )?'
    r'\[(?P<kind>step|warning|prerequisite):(?P<id>[a-z0-9-]+)'
    r'(?: steps=(?P<targets>[a-z0-9,-]+|\*))?\] (?P<text>.+)\Z'
)


def strict_json(text: str):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise SourceValidationError(f'Duplicate JSON key: {key}')
            result[key] = value
        return result

    try:
        return json.loads(text, object_pairs_hook=pairs)
    except (TypeError, json.JSONDecodeError) as exc:
        raise SourceValidationError('Invalid source JSON') from exc


def identifier(value, name: str) -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise SourceValidationError(f'Invalid {name}')
    return value


def parse_document(raw: bytes) -> Document:
    if len(raw) > MAX_SOURCE_BYTES:
        raise SourceValidationError('Document exceeds source-size limit')
    try:
        source = raw.decode('utf-8')
    except UnicodeDecodeError as exc:
        raise SourceValidationError('Source must be UTF-8') from exc
    if '\x00' in source or '\r' in source.replace('\r\n', ''):
        raise SourceValidationError('NUL and standalone carriage returns are unsupported')
    tokens = MarkdownIt('commonmark', {'html': False}).parse(source)
    if not tokens or tokens[0].type != 'fence' or tokens[0].info != 'sop-metadata':
        raise SourceValidationError('First block must be a sop-metadata JSON fence')
    meta = strict_json(tokens[0].content)
    fields = {'document_id', 'version', 'title', 'effective_date', 'procedure_key',
              'scope', 'supersedes', 'data_mode'}
    if not isinstance(meta, dict) or set(meta) != fields:
        raise SourceValidationError('Metadata fields do not match the source schema')
    for key in ('document_id', 'version', 'procedure_key', 'scope'):
        identifier(meta[key], key)
    if meta['data_mode'] != 'synthetic':
        raise SourceValidationError('Only fictional synthetic documents are permitted')
    if not isinstance(meta['title'], str) or not meta['title'].strip():
        raise SourceValidationError('Document title is required')
    try:
        if date.fromisoformat(meta['effective_date']).isoformat() != meta['effective_date']:
            raise ValueError()
    except (ValueError, TypeError) as exc:
        raise SourceValidationError('Effective date must be YYYY-MM-DD') from exc
    if not isinstance(meta['supersedes'], list):
        raise SourceValidationError('supersedes must be a list of versions')
    for version in meta['supersedes']:
        identifier(version, 'superseded version')
    if len(set(meta['supersedes'])) != len(meta['supersedes']) or meta['version'] in meta['supersedes']:
        raise SourceValidationError('Invalid supersession references')

    lines = source.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    headings = []
    title_count = 0
    for index, token in enumerate(tokens):
        if token.type != 'heading_open':
            continue
        content = tokens[index + 1].content
        if token.level != 0:
            raise SourceValidationError('Section headings must be top-level blocks')
        if token.tag == 'h1':
            title_count += 1
            if content != meta['title'] or headings:
                raise SourceValidationError('H1 must match the metadata title before sections')
        elif token.tag == 'h2':
            match = _HEADING.fullmatch(content)
            if not match:
                raise SourceValidationError('Each H2 needs an explicit {#section-id}')
            identifier(match[2], 'section ID')
            headings.append((token.map[0], match[2], match[1]))
        else:
            raise SourceValidationError('Use H2 sections; deeper headings are unsupported')
    if title_count != 1 or not headings:
        raise SourceValidationError('Exactly one document title and at least one section are required')
    if len({item[1] for item in headings}) != len(headings):
        raise SourceValidationError('Duplicate section ID')
    sections = []
    for index, (line, section_id, title) in enumerate(headings):
        end_line = headings[index + 1][0] if index + 1 < len(headings) else len(lines)
        start, end = offsets[line], offsets[end_line]
        if end - start > MAX_SECTION_CHARS:
            raise SourceValidationError(f'Section {section_id} is too large; split it explicitly')
        sections.append(Section(section_id, title, source[start:end], start, end))

    blocks = []
    for token in tokens:
        if token.type == 'list_item_open':
            original = lines[token.map[0]].rstrip('\r\n')
            match = _BLOCK.fullmatch(original)
            if not match or match['kind'] != 'step':
                raise SourceValidationError('Every list item must be an explicitly identified step')
        if token.type != 'inline' or not token.map:
            continue
        line = token.map[0]
        original = lines[line].rstrip('\r\n')
        match = _BLOCK.fullmatch(original)
        if not match:
            if re.search(r'\[(?:step|warning|prerequisite):', token.content):
                raise SourceValidationError('Malformed source annotation')
            continue
        if token.map[1] != line + 1:
            raise SourceValidationError('Annotated blocks must occupy one source line')
        owner = next((s for s in sections if s.start <= offsets[line] < s.end), None)
        if owner is None:
            raise SourceValidationError('Annotated blocks must belong to a section')
        kind = match['kind']
        if (kind == 'step') != (match['number'] is not None):
            raise SourceValidationError('Steps must be numbered; other blocks must not be numbered')
        targets = match['targets']
        if kind == 'step' and targets is not None:
            raise SourceValidationError('Steps cannot declare warning relationships')
        if kind != 'step' and targets is None:
            raise SourceValidationError('Warnings and prerequisites need explicit steps= targets')
        block_id = identifier(match['id'], 'block ID')
        start = offsets[line] + match.start('text')
        end = offsets[line] + match.end('text')
        blocks.append(Block(block_id, kind, source[start:end], owner.section_id, start, end,
                            tuple(targets.split(',')) if targets else (),
                            int(match['number']) if match['number'] else None))
    if len({block.block_id for block in blocks}) != len(blocks):
        raise SourceValidationError('Duplicate block ID')
    steps = [block for block in blocks if block.kind == 'step']
    if not any(block.kind == 'warning' for block in blocks):
        raise SourceValidationError('Each demo procedure requires an explicit warning block')
    if not steps or [step.order for step in steps] != list(range(1, len(steps) + 1)):
        raise SourceValidationError('Procedure steps must have consecutive document-wide order')
    step_ids = {step.block_id for step in steps}
    for block in blocks:
        if block.applies_to == ('*',):
            continue
        if len(set(block.applies_to)) != len(block.applies_to) or not set(block.applies_to) <= step_ids:
            raise SourceValidationError('Unknown or duplicate warning/prerequisite step reference')
    return Document(meta['document_id'], meta['version'], meta['title'], meta['effective_date'],
                    meta['procedure_key'], meta['scope'], tuple(meta['supersedes']), source,
                    sha256(raw).hexdigest(), tuple(sections), tuple(blocks))


def chunk_document(document: Document) -> tuple[Chunk, ...]:
    # Complete sections are intentionally small; oversize sections fail ingestion.
    return tuple(Chunk(stable_id(document.document_id, document.version, section.section_id,
                                CHUNKER_VERSION), document.document_id, document.version,
                       section.section_id, f'{document.title}: {section.title}', section.text)
                 for section in document.sections)
