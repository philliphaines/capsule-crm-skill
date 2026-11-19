# Gotchas

Learned against live Capsule accounts. Where these disagree with Capsule's docs, the live
behaviour won.

## Paging

- **Parse the `Link` header between `<` and `>`, never by splitting on commas.** Next links
  contain commas themselves (`embed=tags,fields`). `rel` may be quoted or not
  (`rel=next`), may hold several values (`rel="next last"`), and the target may be relative
  (`</api/v2/kases?page=2>`), resolving against `https://api.capsulecrm.com`.
- **A full page with no next link isn't necessarily the end.** If a page comes back full
  (`perPage` items) without a next link, ask for `page + 1` anyway; stop at the first page that
  isn't full and has no next link. A missing or unreadable header must never cut a download
  short. (`scripts/capsule.py --all` does both.)
- Default `perPage` is 50; always ask for 100 on bulk reads.

## Incremental sync

- `since` works on `/parties`, `/opportunities` and `/kases`. Write it as ISO 8601 UTC with
  whole seconds: `2026-11-17T09:00:00Z`.
- Ask for `since = last run's start − 5 minutes` to absorb clock skew; saving a record twice is
  harmless, missing one isn't. Record the run's *start* time, not its end.
- Pair it with `/{entity}/deleted?since=…` for removals (`since` is required there). That reply
  can also include `restrictedParties` / `restrictedOpportunities` / `restrictedKases`: records
  the user can no longer see.
- **Tasks can't be fetched by change date.** List all open tasks each time and treat any you
  stored that are missing as completed, deleted or reassigned.

## Reading leniently

- Any field may be null or missing, including `name`, nested `id`s and timestamps; unknown
  fields appear without warning. Skip bad items rather than failing a whole run.
- Timestamps come with or without fractional seconds.
- Custom field values have only `definition.id` and `definition.name`; skip values with no
  value, no definition id or no name. Booleans may arrive as JSON booleans.
- Tags with no name: skip them.

## Opportunities

- **`GET /milestones` returns only the account's first pipeline.** For every milestone, take
  those, then `GET /pipelines` and fetch `/pipelines/{id}/milestones` for each pipeline whose id
  none of them has.
- Status is derived: open without `closedOn`; otherwise lost if `lostReason` has a name or the
  milestone is named "Lost" (case-insensitive); otherwise won.
- **Line items are undocumented.** `embed=lineItems` on the list gives only each line's `id`
  (enough to know an opportunity has products). For the details, fetch one opportunity with
  `?embed=lineItems&sideload=true`: lines have `product` (a product id), `quantity` (missing
  means 1), `unitPrice` (missing means 0), `taxRate` (a percentage) and `discount`
  `{amount, discountType}` (`PERCENTAGE`, case-insensitive, or an amount off). Name them from
  `/products`.
- **`sideload=true` turns every other nested object into a bare id.** Read only `lineItems`
  from that reply. (On `/products?embed=prices`, though, `sideload=true` is what turns each
  price's `market` *into* an object.)
- An opportunity's `market` only appears with `embed=market`. Without it, don't read its
  absence as "no market".
- Products and payment terms don't mix. With line items, Capsule calculates the value itself and
  forces `durationBasis` to `FIXED` ([writing.md](writing.md#products-line-items)).
- `durationBasis` may be missing or hold a value you don't recognise: treat it as `FIXED`, and
  ignore a `duration` that comes with `FIXED`.
- Writing line items: `product` is required even on a removal, `quantity` must be an integer,
  and an amount discount is `FIXED`, not `AMOUNT`.

## Text Capsule can't take

- Limits are per field and counted in code points; an opportunity name is only 100, a project
  name 255, most other short fields 250 ([writing.md](writing.md#text-limits)).
- **Characters above U+FFFF (most emoji) can't be stored.** Most fields accept them with 200 and
  store "��", which quietly damages the text. An organisation name, a person's title and an
  email address fail with HTTP 500 "Internal Server Error". Treat a 500 on a write as a
  refusal that probably comes from such characters, not as an outage, and don't retry it
  unchanged.
- `GET /titles` leaves out Capsule's built-in titles unless you add `includeBuiltinTitles=true`.
- Addresses take the country's English name from `/countries`, not its ISO code.

## Projects

- **Never send `embed=opportunity` to `GET /kases` (the list).** With it Capsule returned a
  single project instead of the page.
- The list has been seen returning `name: null` for projects that do have a name. Re-fetch
  those with `GET /kases/{id}?embed=tags,fields`.
- A project's `opportunity` in the list has an id but no name: look it up yourself.
- The API calls projects `kases` and the body key is `kase`; the web app's URL is
  `/project/{id}`.

## Tasks and tracks

- `GET /tasks` returns open tasks unless you pass `status`.
- `hasTrack: true` says a task is on a track but not which, even with `embed=track`. To find it,
  ask the task's record (`/parties|opportunities|kases/{id}/tracks`; contact first, then
  opportunity, then project) and match the task ids in each track's `tasks`. A 403 or 404 there
  means you can't tell. A task never changes track.
- A task's `category` comes back with `id`, `name` and `colour` (checked live 2026-11-17;
  older notes say name and colour only). If the id is ever missing, match the name in
  `/categories`. Set it with `{"id": …}`.
- A task's due moment is `dueOn` at `dueTime` in the user's time zone, or the start of the day
  without a time.

## History

- Per-record `/entries` allow `perPage` up to 50, `/entries` up to 100. Both are newest first.
- An organisation's history doesn't include its people's notes unless you add
  `includeLinked=true` (undocumented, confirmed live).
- Emails list their contacts in `parties` (an array); notes use `party`.
- Creating a note: `activityType` is a bare integer, not an object. Built-in activity types
  have negative ids.
- Upload attachments first (`POST /attachments/upload` with the file's own `Content-Type` and a
  URL-encoded `X-Attachment-Filename`), then send the tokens in the note's `attachments`.

## Writing

- Send only what changed; `null` clears; nested items go by `id` with `_delete: true` to remove
  ([writing.md](writing.md)).
- Tags match by name case-insensitively. Removing a tag the record never had in Capsule (no id)
  sends nothing.
- A brand-new person can be linked to a brand-new organisation in one go with
  `"organisation": {"name": "…"}`, but if you're creating both yourself, create the
  organisation first and link by id.
- When Capsule refuses a change, show `message` followed by each `errors[].message`, joined with
  spaces, skipping blanks. If there's nothing useful, say "Capsule couldn't save the change
  (HTTP *status*)."
- On a refused write: 422/400 means fix the body; 403 means no permission (read-only token or
  restricted record); 404 means the record was deleted in Capsule meanwhile; 500 most likely
  means characters Capsule can't store (see above).

## Rate limits and retries

- 4,000 requests per hour per user. Successful replies carry `X-RateLimit-Limit`,
  `X-RateLimit-Remaining` and `X-RateLimit-Reset` (epoch seconds).
- On 429, wait for `Retry-After` if present, else until `X-RateLimit-Reset`, else 5 seconds;
  try up to 3 times, then stop. Hammering after a 429 can get the app blocked or the user
  disabled.
- On 401 with OAuth, refresh the token once and retry; a second 401 means sign in again.

## Debugging

- When data looks missing, compare a live `GET` with what your code stored before changing
  code. Two bugs (a comma-splitting Link parser and `embed=opportunity`) took minutes
  to find this way and hours to guess at.
- Only GETs and filter queries are safe to probe a real account with.
