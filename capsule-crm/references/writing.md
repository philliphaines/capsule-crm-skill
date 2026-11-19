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
- **Check text before sending** against the limits and characters below.

## Text limits

Measured live on 2026-11-19. Lengths count Unicode code points after trimming surrounding
spaces: "é" counts once, but "e" plus a combining accent counts twice. Over the limit, Capsule
replies 422 "size must be between 0 and 250" (addresses say "invalid address", custom fields
"invalid value for custom field").

| Field | Limit |
|---|---|
| Person `firstName`, `lastName`, `jobTitle`; organisation `name` | 250 |
| Phone `number`, email `address`, website `address` | 250 |
| Address `street`, `city`, `state`, `zip` | 250 |
| Custom text field value | 250 |
| Task `description` (title) | 250 |
| Opportunity `name` | **100** |
| Project `name` | **255** |
| Task `detail` | 8,000 |
| Party `about`, opportunity and project `description`, note `content` | 16,000 |

Tag name limits haven't been measured.

**Capsule can't store characters above U+FFFF**: most emoji (😀, 🎉), and rare CJK such as
𠀀. That holds whether they're sent as UTF-8 or as `😀` escapes. Most fields reply
200 but store "��" instead, so the text is quietly damaged. An organisation's `name`, a
person's `title` and an email `address` fail with **500** instead. Characters up to U+FFFF are
fine, including ☀️, ❤️, accented and macronised letters (Māori) and common CJK. Tell the user
which characters can't be saved; don't strip or swap them silently. `scripts/capsule.py`
refuses to send them.

## Required names

A person needs a `firstName` or `lastName`; an organisation, opportunity or project needs a
`name`; a task needs a `description` and `dueOn`.

## Titles and countries

- A person's `title` should be one of `/titles?includeBuiltinTitles=true` (an account can add up
  to 50 of its own).
- An address's `country` is a country `name` from `/countries` in English ("United Kingdom",
  "New Zealand"), not an ISO code. (Filters use codes: `country is "GB"`.)

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
- Read and write with `?embed=tags,fields,market` so the reply shows the opportunity's market.

### Payment terms

`durationBasis` is one of `FIXED`, `HOUR`, `DAY`, `WEEK`, `MONTH`, `QUARTER`, `YEAR`; a missing
basis means `FIXED`. For anything but `FIXED`, `value` is per period and `duration` is the
number of periods (a whole number, at least 1); the total is value × duration.

```json
{"opportunity": {"value": {"amount": 500, "currency": "GBP"}, "durationBasis": "MONTH", "duration": 12}}
```

- Always send `durationBasis` and `duration` together. A basis other than `FIXED` without a
  duration of at least 1 gets 422. With `FIXED`, Capsule clears the duration itself.
- A new opportunity needs the terms only when they aren't `FIXED`.

### Products (line items)

An opportunity's value comes **either** from products **or** from an amount with payment
terms, never both. Once an opportunity has line items, Capsule works the value out from them
(after discount, with tax), sets the currency to the market's and keeps the terms `FIXED`. So
don't send `value`, `durationBasis` or `duration` for an opportunity with products.

Products are priced per **market** (`/markets`). A product can go on an opportunity in a market
when its `status` is `active` and it has a price in that market
(`/products?embed=prices&sideload=true`). Send `market` with the opportunity's first products:

```json
{"opportunity": {
  "market": {"id": 2},
  "lineItems": [
    {"product": {"id": 77}, "quantity": 3, "discount": {"amount": 10, "discountType": "PERCENTAGE"}, "taxRate": 20},
    {"id": 5501, "product": {"id": 78}, "quantity": 2, "discount": null, "taxRate": null},
    {"id": 5502, "product": {"id": 79}, "_delete": true}
  ]
}}
```

Checked live on 2026-11-18:

- A line without `id` is **added** to the existing lines. Capsule prices it from the market;
  don't send a price.
- A line with `id` **changes** that line; `"discount": null` and `"taxRate": null` clear them.
- `{"id": …, "product": {"id": …}, "_delete": true}` **removes** a line. `product` is required on
  every line, even one being removed ("product is required").
- `quantity` must be a whole number, and is required when adding.
- `discountType` is `PERCENTAGE` or `FIXED` (an amount off). `AMOUNT` is refused.
- `taxRate` is a percentage, such as `20`.
- Removing the last line leaves the value at 0 in the market's currency; the market stays.
- To see the lines afterwards, fetch `GET /opportunities/{id}?embed=lineItems&sideload=true`.
  A PUT's reply doesn't list them.

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
