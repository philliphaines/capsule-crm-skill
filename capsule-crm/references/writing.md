# Writing to Capsule

Every body is wrapped in the record's singular key. POST creates (201, `Location` header, the
stored record in the body); PUT updates (200, the full record). Add `?embed=tags,fields` to a
POST or PUT to get tags and custom fields back in the reply.

## General rules

- **Only what changes.** Fields left out of a PUT stay as they are. Don't echo back a whole
  record you fetched: you'd overwrite someone else's change to another field.
- **`null` clears** a scalar field or a link (`"organisation": null`, `"expectedCloseOn": null`).
- **Links go by id:** `{"id": 123}`, never a name, except the organisation shortcut below.
- **Nested lists** (`phoneNumbers`, `emailAddresses`, `addresses`, `websites`, `tags`,
  `fields`, entry `attachments`) are merged, not replaced:
  - new item: no `id`;
  - changed item: its `id` plus the changed keys;
  - removed item: `{"id": 456, "_delete": true}`.
  Leave empty item keys out rather than sending them as `null`.
- **Dates** are `YYYY-MM-DD`; times of day `HH:mm:ss`.

## Contacts

```json
{"party": {
  "type": "person",
  "title": "Dr", "firstName": "Sam", "lastName": "Lee", "jobTitle": "Buyer",
  "organisation": {"id": 4},
  "emailAddresses": [{"type": "Work", "address": "sam@acme.test"}],
  "phoneNumbers": [{"type": "Mobile", "number": "07700 900123"}],
  "websites": [{"service": "URL", "address": "samlee.test"}],
  "addresses": [{"type": "Office", "street": "1 High St", "city": "Leeds", "zip": "LS1 1AA", "country": "United Kingdom"}],
  "tags": [{"name": "Customer"}],
  "fields": [{"definition": {"id": 70}, "value": "A-100"}]
}}
```

- `type` is required on create and can't change. An organisation needs `name`; a person needs
  `firstName` or `lastName`.
- `organisation` takes `{"id": N}` for an existing one, `{"name": "Acme"}` to create one on the
  fly, or `null` to unlink.
- Websites need a `service` (`URL`, `LINKED_IN`, `TWITTER`, `FACEBOOK`, `SKYPE`…); use `URL` for
  a plain web address. Capsule builds the full `url` itself.
- Change a phone number: `"phoneNumbers": [{"id": 1, "number": "01234 000000"}]`.
  Remove one: `"phoneNumbers": [{"id": 1, "_delete": true}]`.
- `owner: {"id": userId}` and `team: {"id": teamId}` assign the contact.

## Tags

- Add a tag **by name**: `{"name": "Hot"}`. Capsule reuses an existing tag with that name or
  creates it. Compare names case-insensitively before adding, so you don't add one the record
  already has.
- Remove a tag **by its id**: `{"id": 40, "_delete": true}` (the id is in the record's
  `tags`, from `embed=tags`).
- A DataTag (`dataTag: true`) carries its own custom fields; adding it makes them available.

## Custom field values

Look up definitions first: `GET /{parties,opportunities,kases}/fields/definitions`.

| To | Send in `fields` |
|---|---|
| Set a value the record doesn't have | `{"definition": {"id": 70}, "value": "A-100"}` |
| Change an existing value | `{"id": 9001, "value": "A-200"}` (the value's own id, from `embed=fields`) |
| Remove a value | `{"id": 9001, "_delete": true}` |

Boolean fields take JSON `true`/`false`; date fields `YYYY-MM-DD`; list fields one of the
definition's `options`. A field belonging to a DataTag only accepts a value when the record has
that tag.

## Opportunities

```json
{"opportunity": {
  "name": "Website redesign",
  "party": {"id": 11587},
  "milestone": {"id": 3},
  "owner": {"id": 4},
  "value": {"amount": 12000, "currency": "GBP"},
  "expectedCloseOn": "2026-12-31",
  "probability": 50,
  "description": "Phase one",
  "tags": [{"name": "Inbound"}]
}}
```

- Milestones belong to pipelines; pick from `/pipelines/{id}/milestones`, not `/milestones`.
- Close as lost: set the pipeline's Lost milestone and `"lostReason": {"id": N}`. Close as won:
  set the Won milestone. Capsule fills `closedOn`.
- `value` with no `currency` uses the account's default; `"value": null` clears it.
- Additional contacts aren't in the body: `POST /opportunities/{id}/parties/{partyId}`.

## Projects (kases)

```json
{"kase": {
  "name": "Onboarding",
  "party": {"id": 11587},
  "opportunity": {"id": 1},
  "stage": {"id": 20},
  "owner": {"id": 4},
  "status": "OPEN",
  "startOn": "2026-11-20",
  "expectedCloseOn": "2027-01-31",
  "description": "…"
}}
```

`status` is `OPEN` or `CLOSED`. Stages belong to boards (`/boards/{id}/stages`).

## Tasks

```json
{"task": {
  "description": "Call Sam",
  "detail": "About the order",
  "dueOn": "2026-11-20",
  "dueTime": "09:30:00",
  "category": {"id": 60},
  "owner": {"id": 4},
  "party": {"id": 11587}
}}
```

- `description` is the task's title; `detail` the longer text.
- Link to at most one of `party`, `opportunity` or `kase`; leave all out for a standalone task.
- Complete: `{"task": {"status": "COMPLETED"}}`. Snooze: send a new `dueOn` only.
- Clearing: `"dueTime": null`, `"category": null`, `"detail": null`. The owner can't be cleared.
- Category ids are in `/categories` (and usually on the task's own `category`).

## Tracks

```json
{"track": {"definition": {"id": 105022}, "trackDateOn": "2026-12-15", "kase": {"id": 300}}}
```

Exactly one of `party`, `opportunity`, `kase`, matching the definition's `captureRule`
(PARTY, OPPORTUNITY, CASEFILE). For a definition whose `direction` is `END_DATE`,
`trackDateOn` is the end date the tasks count back from. Capsule creates the tasks itself.

## Notes and attachments

1. Upload each file: `python3 scripts/capsule.py upload report.pdf --confirm` →
   `{"upload": {"token": "…"}}`.
2. Create the note:

```json
{"entry": {
  "type": "note",
  "content": "Met at the show",
  "activityType": -2,
  "attachments": [{"token": "…"}],
  "party": {"id": 11587}
}}
```

- `type` must be `note`; emails and completed tasks can't be created.
- `activityType` is a **bare id**, not `{"id": …}`. Leave it out for a plain note.
- File the note under exactly one of `party`, `opportunity` or `kase`. A note on an opportunity
  or project has no `party`.
- Only read `entry.id` from the reply before treating the note as saved, so a surprising reply
  can't make you send it twice.
- Edit later with `PUT /entries/{id}`: new `content`, add `{"token": …}`, remove
  `{"id": N, "_delete": true}`. Removing the last attachment from a note with no content fails;
  delete the entry instead.

## Deleting

`DELETE /parties|opportunities|kases|tasks|entries/{id}` is permanent: 204, or 202 with a job to
poll for big records. Always confirm the exact record (name and id) with the user first.
