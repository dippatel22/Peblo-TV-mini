# Peblo TV Mini

A small, deliberately boring content pipeline: editors manage shows and episodes in the CMS, an admin publishes a validated catalogue, and the viewer only reads that published JSON. The UI is intentionally restrained rather than trying to imitate a full streaming product.

## Run it

```bash
docker compose up --build
```

Open **CMS** at `http://localhost:5173` and **Viewer** at `http://localhost:5174`.

Demo accounts:
- admin / admin123 — editor + publish
- editor / editor123 — CRUD only

The API is at `http://localhost:8000/docs`; health is `GET /health`.

**Operability.** The first alert I would add is on a publish run ending in `blocked` or an unexpected `failed` state. A stale viewer catalogue is usually a product incident even when the API itself is healthy, so this catches the actual publishing path rather than only checking liveness.

The compose startup runs the migration and imports the supplied 95-row seed. The importer keeps the database uniqueness constraint intact: the deliberately duplicated Hindi content-group row is recorded as a fixable validation issue instead of being inserted twice. It also creates a safe initial catalogue from rows that pass the same publication gates, so the viewer has something to show while the CMS reports the outstanding fixes.

## Decisions / trade-offs

**Atomic publish.** A publish run first builds deterministic JSON in memory, writes a versioned `catalog.<run>.json`, then writes `catalog.json` through a temporary file + `os.replace`. Readers therefore see either the old complete catalogue or the new complete catalogue. If the process dies before the replace, the old file remains live; unused versioned files are retained for inspection. Re-running the same data produces the same content hash. In production on R2 I would upload an immutable version and atomically switch a small pointer/manifest rather than trying to rename an object.

**Storage abstraction.** Artwork uses a `Storage` interface and the current `LocalStorage` implementation. Moving to Cloudflare R2 changes the implementation of `save_bytes`, `read_bytes`, and `atomic_publish`; API/business code does not change. Production credentials would live in the deployment secret store, never in the repo or `.env` checked into source control.

**Search.** Viewer search runs against the published catalogue, not the admin database. That makes the read path simple and guarantees viewers never see drafts. It is fine for this challenge and probably for tens of thousands of catalogue entries. At a much larger catalogue, JSON download/search becomes the bottleneck; I would move search to a dedicated indexed read model (Postgres full-text or OpenSearch), while keeping publication as the source of truth.

**Why a published file?** The viewer is a read-heavy surface and should not couple itself to CMS tables, joins, drafts, or permissions. A prebuilt file is cacheable at the edge and gives every viewer the same snapshot. The trade-off is publication latency/staleness and the need to make the publish pipeline reliable. Search also has to operate on the published representation rather than the richer CMS model.

**Seed issues found.** `ep_0036` is published without artwork; `ep_9001` duplicates an existing `(content_group, language)` pair and has a conflicting title; `Rhyme Rangers` is a draft with no section (warning, not a blocker). Season 0 is treated as trailers and excluded from normal season lists, while its thumbnail is enough for the trailer surface.

**Left out.** I did not build video playback, real user provisioning, R2 itself, rollback/diff UI, or an audit log. Those are useful next steps but do not improve the core CMS → publish → catalogue flow for this take-home. The demo auth deliberately uses two local accounts so role enforcement can be exercised without introducing an unrelated identity provider.

**AI use.** AI was used as a coding assistant for scaffolding and to catch a few implementation mistakes. The important decisions here—especially how the bad seed row is represented, what blocks publication, the catalogue shape, and the atomic file swap—were reviewed against the supplied challenge/reference rather than accepted blindly.

## Project layout

- `backend/` — FastAPI, SQLAlchemy, Alembic, validation, storage, tests
- `cms/` — React + TypeScript + TanStack Query internal CMS
- `viewer/` — separate React + TypeScript viewer using only `/catalog*`
- `storage/` — local storage backend and demo artwork
- `.github/workflows/ci.yml` — tests, type checks, frontend builds, Docker builds

## Artwork rules

The API enforces the supplied limits server-side: poster 2:3 around 600×900, banner 16:9 around 1280×720, thumbnail 16:9 around 640×360, each at or below 200 KB. The CMS repeats those requirements beside every upload slot and shows the server's human-readable error when an upload is rejected.

## Rough time spent

Backend/data model + publish pipeline: ~3 hours  
CMS: ~2.5 hours  
Viewer: ~1.5 hours  
Compose/CI/tests/README: ~1 hour
"# Peblo-TV-mini" 
