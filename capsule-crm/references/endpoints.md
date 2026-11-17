# Capsule API v2 endpoints

Base: `https://api.capsulecrm.com/api/v2`. Paging: `page` (from 1) and `perPage` (default 50,
max 100; per-record entries max 50). Follow the `Link` header's `rel="next"`
([gotchas](gotchas.md#paging)). `embed` takes a comma-separated list.

## Account and settings

| Method | Path | Notes |
|---|---|---|
| GET | `/site` | `site.name`, `site.subdomain` |
| GET | `/users/current` | The token's user (`id`, `username`) |
| GET | `/users` | Everyone in the account; owners are referenced by these ids. Each has a default `currency` |
| GET | `/teams` | Teams, for `team` on records |
| GET | `/{parties,opportunities,kases}/tags` | Every tag in the account for that kind of record |
| GET | `/{parties,opportunities,kases}/fields/definitions` | Custom fields: `id`, `name`, `type` (text, date, list, multiselectlist, boolean, number, link…), `options`, `tag` (DataTag), `captureRule` |
| GET | `/pipelines`, `/pipelines/{id}/milestones` | Pipelines and their milestones |
| GET | `/milestones` | **Only the first pipeline's** milestones ([gotchas](gotchas.md#opportunities)) |
| GET | `/lostreasons` | Reasons an opportunity can be lost |
| GET | `/currencies` | Not paged |
| GET | `/products` | Products for opportunity line items (`id`, `name`, `sku`) |
| GET | `/boards`, `/boards/{id}/stages` | Project boards and stages (`displayOrder`) |
| GET | `/categories` | Task categories (`id`, `name`, `colour`). Not paged |
| GET | `/activitytypes` | Note activity types (Meeting, Call…). Ids can be negative (built-ins) |
| GET | `/trackdefinitions` | Track templates: `description` (name), `captureRule` (PARTY, OPPORTUNITY, CASEFILE), `direction` (START_DATE, END_DATE) |

## Contacts (parties)

Embeds: `tags`, `fields`, `organisation`, `missingImportantFields`.

| Method | Path | Notes |
|---|---|---|
| GET | `/parties` | `since` (ISO 8601 UTC) for changes only |
| GET | `/parties/{id}` or `/parties/{id1},{id2},…` | Up to 10 ids; 404 if any is missing |
| GET | `/parties/search?q=` | Same as Capsule's global search (name, email, phone, postcode) |
| POST | `/parties/filters/results` | Structured query ([filters.md](filters.md)) |
| GET | `/parties/{id}/people` | People employed by an organisation |
| GET | `/parties/{id}/opportunities`, `/parties/{id}/kases` | A contact's opportunities and projects |
| GET | `/parties/{id}/entries` | History, newest first; `includeLinked=true` adds an organisation's people's, opportunities' and projects' entries |
| GET | `/parties/{id}/tracks` | Tracks applied to the contact |
| GET | `/parties/deleted?since=` | Deleted (and newly restricted) ids since a time. `since` required |
| POST | `/parties` | `{"party": {...}}` → 201 |
| PUT | `/parties/{id}` | Only changed fields |
| DELETE | `/parties/{id}` | 204, or 202 if scheduled |

## Opportunities

Embeds: `tags`, `fields`, `party`, `milestone`, `lineItems`, `missingImportantFields`.

| Method | Path | Notes |
|---|---|---|
| GET | `/opportunities` | `since` supported |
| GET | `/opportunities/{id}` or up to 10 ids | `?embed=lineItems&sideload=true` for full line items ([gotchas](gotchas.md#opportunities)) |
| GET | `/opportunities/search?q=` | |
| POST | `/opportunities/filters/results` | |
| GET | `/opportunities/{id}/parties` | Additional contacts |
| POST / DELETE | `/opportunities/{id}/parties/{partyId}` | Add / remove an additional contact (204) |
| GET | `/opportunities/{id}/kases` | Projects linked to it |
| GET | `/opportunities/{id}/entries`, `/opportunities/{id}/tracks` | |
| GET | `/opportunities/deleted?since=` | |
| POST | `/opportunities` | `{"opportunity": {...}}`; needs `name`, `party`, `milestone` |
| PUT | `/opportunities/{id}` | |
| DELETE | `/opportunities/{id}` | Permanent |

## Projects (kases)

Embeds: `tags`, `fields`, `party`, `opportunity`, `missingImportantFields` — but never put
`opportunity` on the **list** ([gotchas](gotchas.md#projects)).

| Method | Path | Notes |
|---|---|---|
| GET | `/kases` | `since` supported |
| GET | `/kases/{id}` or up to 10 ids | |
| GET | `/kases/search?q=` | |
| POST | `/kases/filters/results` | |
| GET | `/kases/{id}/parties`; POST / DELETE `/kases/{id}/parties/{partyId}` | Additional contacts |
| GET | `/kases/{id}/entries`, `/kases/{id}/tracks` | |
| GET | `/kases/deleted?since=` | |
| POST | `/kases` | `{"kase": {...}}`; needs `name`, `party` |
| PUT / DELETE | `/kases/{id}` | |

## Tasks and tracks

Task embeds: `party`, `opportunity`, `kase`, `owner`, `nextTask`.

| Method | Path | Notes |
|---|---|---|
| GET | `/tasks` | Open tasks only unless `status=open,completed,pending`. **No `since`** |
| GET | `/tasks/{id}` | |
| POST | `/tasks` | `{"task": {...}}`; needs `description` (the title) and `dueOn` |
| PUT | `/tasks/{id}` | `{"task": {"status": "COMPLETED"}}` completes it |
| DELETE | `/tasks/{id}` | Permanent |
| POST | `/tracks` | Applies a track definition to one record; Capsule creates its tasks |
| GET / DELETE | `/tracks/{id}` | |

## History (entries) and attachments

Entry embeds: `party`, `kase`, `opportunity`, `creator`, `activityType`.

| Method | Path | Notes |
|---|---|---|
| GET | `/entries` | Whole account, newest first, `perPage` up to 100 |
| GET | `/{parties,opportunities,kases}/{id}/entries` | One record, `perPage` up to 50 |
| GET | `/entries/{id}` | |
| POST | `/entries` | Notes only (`type: note`) |
| PUT | `/entries/{id}` | Notes and emails: `content`, add/remove attachments |
| DELETE | `/entries/{id}` | Also deletes its attachments |
| POST | `/attachments/upload` | Raw bytes, `Content-Type`, `X-Attachment-Filename` (URL-encoded) → `upload.token` |
| GET | `/attachments/{id}` | The file; name in `Content-Disposition` |

Entry types: `note` (list, show, create, update), `email` (list, show, update), `task`
(completed tasks; list and show only). Emails name their contacts in `parties`, not `party`.

## REST hooks (webhooks)

Admin users, through a registered OAuth app only; at most 20 per account.

| Method | Path | Notes |
|---|---|---|
| GET | `/resthooks`, `/resthooks/{id}` | Only the calling app's hooks |
| POST | `/resthooks` | `{"restHook": {"event": "party/created", "targetUrl": "https://…", "description": "…"}}` |
| DELETE | `/resthooks/{id}` | |

Events follow `<entity>/<action>` (`party/created`, `party/updated`, `party/deleted`,
`opportunity/…`, `kase/…`, `task/…`, and so on). Check Capsule's REST Hook model page for the
current list before relying on one.

## Jobs

| Method | Path | Notes |
|---|---|---|
| GET | `/jobs/{id}` | From a 202's `Location`: `job.status` (`completed`…), `job.progress` 0–100 |
