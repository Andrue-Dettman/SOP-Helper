# Fictional SOP corpus

These procedures are invented demonstration material, not employer procedures or certified operational guidance. They describe sample records; the assistant does not write inventory or perform the described warehouse actions.

`manifest.json` explicitly selects eight current documents and retains the first receiving version as historical. Ingestion reads only manifest entries. This README is not indexed. Content for an existing document/version is immutable once published; corrections need a new version. Version labels are opaque strings.

Each Markdown document begins with a `sop-metadata` fenced JSON object containing exactly `document_id`, `version`, `title`, `effective_date`, `procedure_key`, `scope`, `supersedes`, and `data_mode`. The latter must be `synthetic`. A single H1 matches the metadata title. H2 headings require stable anchors such as `## Terms {#terms}`.

The source format deliberately makes required content explicit:

```text
[prerequisite:receive-pre-01 steps=*] Have the sample delivery note available.

[warning:receive-stop-01 steps=receive-02] If a package is leaking or visibly damaged, stop. Do not open or move it. Contact the demo supervisor.

1. [step:receive-01] Match the delivery reference to the sample delivery note.
2. [step:receive-02] Inspect the packages before opening them.
```

Annotated blocks occupy one source line. Step numbering is consecutive across the document. All list items must be identified steps. Warnings/prerequisites declare either `steps=*` for the procedure or a comma-separated list of step IDs. Every demo procedure needs at least one explicit warning. Glossary text is ordinary prose in a section; it does not become a required step.

The parser uses CommonMark tokens and their source line maps, retaining original UTF-8 text and line endings. It never renders HTML. Source sections are bounded at 12,000 characters and documents at 100,000 bytes; oversized sections fail with an instruction to split them explicitly. A section is one retrieval chunk in this milestone. Its stable identity includes document, version, section, and chunker version.

Retrieved sections carry the complete document's required steps, warnings, and prerequisites, including exact citations for blocks in other sections. G1 must preserve this context when constructing the public procedure response. A short matched glossary section cannot silently remove a stop instruction.

The manifest supports 1–40 document versions, and paths must resolve to unique Markdown files inside the corpus directory. Duplicate identities, broken references, supersession cycles, and in-place source changes are rejected before publication. Conflicting current procedure/scope declarations are retained so the retrieval service can explicitly report them. Malicious-text and conflict scenarios are generated in isolated test fixtures, not normal demo data.
