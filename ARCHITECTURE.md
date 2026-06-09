# DocLite — Architecture & Design Notes

This document explains what was prioritized, how the system is structured, and the
trade-offs accepted for the project's scope.

## Priorities

1. **Correct, enforced authorization.** Role-based access is the spine of the product,
   so it is centralized in one policy object and enforced in the service layer, with
   tests at both the unit and HTTP boundary.
2. **An OOP, layered backend** that demonstrates SOLID — not a flat file of route
   handlers. Extensibility (import/export formats, roles) is shown through polymorphism.
3. **Rich text that round-trips losslessly** through save, reload, restart, versioning,
   and export.
4. **A coherent, real product UX** rather than a thin demo: presence, comments,
   suggestions, history, and export all wired through the UI.

---

## Layered, object-oriented backend

```
api/         Thin FastAPI routers — HTTP only, no business rules.
services/    Use-case classes (DocumentService, SharingService, …). All authorization
             and orchestration live here.
domain/      Role/Action enums + the central PermissionPolicy (pure, persistence-free).
repositories/ Data access. AbstractRepository contract + SqlAlchemyRepository base +
             one concrete repo per aggregate.
models/      SQLAlchemy ORM entities.
schemas/     Pydantic request/response contracts.
core/        Settings, Database, SecurityManager, exceptions, HTML sanitizer.
realtime/    ConnectionManager (WebSocket presence).
importers/   DocumentImporter strategy hierarchy + ImporterFactory.
exporters/   DocumentExporter strategy hierarchy + ExporterFactory.
main.py      Application factory / composition root.
```

### SOLID in practice

- **Single Responsibility.** Routers translate HTTP ⇄ services; services hold rules;
  repositories only persist; the policy only decides permissions; the
  `ConnectionManager` only tracks sockets.
- **Open/Closed.** Adding an import or export format is a new subclass plus one line in
  the factory — existing importers/exporters and all callers are untouched. Adding a
  role or capability is a single edit to the policy matrix.
- **Liskov.** Every concrete repository honors `AbstractRepository`; every importer
  honors `DocumentImporter.import_bytes` (a template method that always sanitizes).
- **Interface Segregation.** Repositories expose narrow, aggregate-specific queries;
  the policy exposes a focused decision API (`role_allows`, `can`, `authorize`).
- **Dependency Inversion.** Services depend on repository abstractions and the policy,
  all injected via FastAPI `Depends` in `api/deps.py` (the composition root). Nothing
  instantiates concrete DB access with hardcoded globals. A request builds the graph:
  `session → repositories → AccessGuard(+policy) → services`.

### The single authorization chokepoint

`PermissionPolicy` owns the entire **role → capability matrix** and nothing else
re-derives permissions. Services never check roles inline; they call
`AccessGuard.require(user, document_id, action)`, which loads the document (or raises
`NotFoundError`) and asks the policy `authorize(...)`. The policy:

- resolves the **effective role** (owner is implied by `Document.owner_id`; otherwise the
  stored share role; otherwise `None`),
- returns `NotFoundError` for users with *no* relationship (so existence is hidden from
  strangers) and `PermissionDeniedError` for users who have a role but lack the
  capability.

The policy is **pure** (no DB) so it is trivially unit-tested; the guard is the only
place that combines it with persistence.

### Custom exceptions → HTTP

`DocLiteError` is the base for `NotFoundError (404)`, `PermissionDeniedError (403)`,
`AuthenticationError (401)`, `ValidationError (422)`, `UnsupportedFileTypeError (415)`,
and `ConflictError (409)`. A centralized handler in `core/exceptions.py` converts any of
them — plus Pydantic validation errors and unexpected exceptions — into the structured
envelope `{"error": {"code", "message"}}`. Stack traces never reach the client.

---

## How rich text is stored

Documents store their body as **sanitized HTML** in `documents.content_html` (and in
every version snapshot and suggestion). HTML was chosen over a structured JSON model
because:

- TipTap emits/consumes HTML natively, so save/reload is lossless with no transform;
- exporters (HTML→Markdown via markdownify, HTML→PDF via reportlab/WeasyPrint) and
  importers (Markdown/DOCX→HTML) all share one representation;
- versions and suggestions are just alternative HTML strings — simple and uniform.

Every body that enters the system passes through an **allowlist sanitizer**
(`core/html_sanitizer.py`, BeautifulSoup-based) that keeps only known formatting tags
and strips `<script>`, event handlers, and `javascript:` URLs — preventing stored XSS.

---

## Import / export strategy hierarchies

**Import.** `DocumentImporter` (abstract) defines `import_bytes` as a *template method*
that converts then always sanitizes. Concrete strategies: `TxtImporter`,
`MarkdownImporter`, `DocxImporter`. `ImporterFactory` resolves the right strategy by file
extension. `ImportService` validates extension + size, runs the importer, and creates a
new document via `DocumentService`.

**Export.** `DocumentExporter` (abstract) renders title + body to bytes with a media
type and extension. Concrete strategies: `MarkdownExporter` (markdownify) and
`PdfExporter`. `ExporterFactory` resolves by format key. `ExportService` authorizes
`EXPORT` then delegates.

**PDF engine choice (trade-off).** WeasyPrint gives the best HTML/CSS fidelity but needs
native system libraries (Pango/Cairo) that are awkward on Windows and minimal containers.
`PdfExporter` therefore **prefers WeasyPrint when it imports successfully** and otherwise
falls back to **reportlab** (pure Python), which parses the sanitized HTML and renders
headings, paragraphs, ordered/unordered lists, blockquotes, and inline bold/italic/
underline. This guarantees PDF export — and the test suite — work on every platform.

---

## Versioning approach

`DocumentVersion` rows are an **append-only** log of `(version_number, title, HTML,
author, label, timestamp)` per document. A snapshot is written when a document is created
(`created`) and on each "Save version" (`save`). `VersionService` lists/previews
versions and **restores non-destructively**: restoring re-saves the document body to the
chosen version's HTML *through the normal save path*, which appends a new version labelled
`restore from vN`. History is therefore never destroyed — restore only ever grows it.

---

## Comment & suggestion model

**Comments** are anchored to a text range via `(anchor_start, anchor_end)` ProseMirror
positions plus the `quoted_text` that was selected. They carry author + timestamp, can be
**resolved** and **replied** to (threaded `CommentReply`), and the frontend re-highlights
the anchored range with a ProseMirror decoration (no marks are written into the saved
HTML, keeping exports clean). Permissions follow the role model — viewers cannot comment.

**Suggestions** are deliberately simple and *correct*: a `Suggestion` stores the full
`proposed_html` alongside the `base_html` it was proposed against, with a status
(`pending`/`accepted`/`rejected`). **The canonical document body is never mutated while a
suggestion is pending.** Accepting (owner/editor only) applies the proposed body through
`DocumentService.save_body` — which also records a version — and marks the suggestion
accepted; rejecting simply marks it rejected and leaves the body untouched. The UI
provides a read-only side-by-side "current vs proposed" preview.

Trade-off: storing whole-body proposals (rather than fine-grained per-edit operations)
keeps the model unambiguous and guarantees the "no silent mutation" property, at the cost
of not showing inline word-level diffs in the document itself.

---

## Real-time presence design

`ConnectionManager` (a.k.a. presence manager) holds, per document, a room of live
WebSocket connections keyed by a connection id (one user may have several tabs; presence
de-duplicates by user). It is a process-wide singleton so HTTP handlers and sockets share
the same rooms.

- **Handshake auth.** The browser passes its JWT as a `?token=` query parameter (the
  WebSocket API can't set Authorization headers). The socket is authenticated *and*
  authorized for `VIEW` using a short-lived DB session before it joins — the long-lived
  socket never pins a database connection.
- **Events.** On join/leave the manager broadcasts a fresh `presence` list (clients just
  replace their list) plus `user_joined`/`user_left`. Clients can emit `activity` ("I'm
  editing"), which is relayed. After a save/restore/accept, the HTTP handler calls
  `notify_document_updated`, broadcasting a `document_updated` event so present users get
  a live banner to reload.

Trade-off (stated in the README): this is **presence + update signaling**, not
conflict-free concurrent co-editing (OT/CRDT), which is out of scope. Comments,
suggestions, and version history make concurrent work safe without full co-editing.

---

## Frontend structure

A cleanly organized (not OOP) React app: `api/` (axios client + endpoint wrappers with
error normalization), `context/` (`AuthContext`, `ToastContext`), `hooks/`
(`useDocumentSocket` for presence), `editor/` (a TipTap `CommentHighlight` extension),
`components/` (Toolbar, PresenceBar, ShareDialog, CommentPanel, SuggestionPanel,
VersionPanel, UploadButton, …), and `pages/` (Login, Dashboard, Editor). Permissions from
the document's `my_role` drive which affordances are enabled, but the server remains the
enforcement authority.

## Testing strategy

`pytest` with an isolated, per-test seeded SQLite database and FastAPI's `TestClient`
(including its WebSocket support). Coverage spans the policy matrix in isolation,
route-level enforcement (403/404/401), import structure preservation (.md and .docx),
the document lifecycle, non-destructive version restore, Markdown + PDF export,
comment/suggestion permissions and the no-silent-mutation guarantee, and live two-client
presence + the document-updated signal.

## Notable trade-offs accepted for scope

- **HTML (not OT/CRDT) document model** — simple, lossless round-trips; no real-time
  merge.
- **Whole-body suggestions** — unambiguous accept/reject; no inline doc diff.
- **reportlab-first PDF** — universal portability over maximum CSS fidelity.
- **SQLite** — zero-config persistence well-suited to this scope; swap `DOCLITE_DATABASE_URL`
  for Postgres if scaling.
- **JWT in localStorage** — straightforward for the demo; a production hardening would
  move to httpOnly cookies with CSRF protection.
