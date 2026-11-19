---
name: capsule-crm
description: Read and change data in Capsule CRM through its REST API v2 (api.capsulecrm.com). Use whenever the user asks about their Capsule contacts (parties, people, organisations), opportunities, pipelines, projects (cases, "kases"), tasks, tracks, notes, history entries, tags or custom fields; wants to search, filter, list, export, create, update or delete Capsule records; or is writing code, an integration or an app that calls the Capsule API (OAuth, paging, sync, webhooks/REST hooks).
metadata:
  version: 1.1.1
  updated: 2026-11-20
---

# Capsule CRM API

Capsule's REST API v2 lives at `https://api.capsulecrm.com/api/v2`. Every request sends
`Authorization: Bearer <token>` and `Accept: application/json`; bodies are JSON wrapped in the
record's singular name (`{"party": {...}}`).

Use the bundled client for live calls. It handles the token, paging, rate limits and Capsule's
error messages, and it refuses writes unless `--confirm` is passed:

```sh
C=scripts/capsule.py   # relative to this skill's directory
python3 $C whoami                                     # which account and user the token is for
python3 $C get parties/search -p q=acme -p embed=tags,fields
python3 $C get opportunities --all -p embed=tags,fields   # every page, merged
python3 $C post parties/filters/results --data '{"filter":{"conditions":[{"field":"tag","operator":"is","value":"VIP"}]}}' --all
python3 $C put parties/123 --data '{"party":{"jobTitle":"Buyer"}}' --confirm
```

## Rules

1. **Reads are free; writes need the user's yes.** GET and `filters/results` queries are safe.
   Before any POST, PUT or DELETE (including an attachment upload), show the user the exact
   method, path and body, and wait for approval. Only then add `--confirm`. Never batch-write
   or delete many records without an explicit go-ahead for that batch.
2. **Never print, log or commit the token.** The client reads it from `$CAPSULE_API_TOKEN`,
   `$CAPSULE_TOKEN_FILE`, a `.capsule-token` file in the working directory or a parent, or
   `~/.config/capsule/token`. If none exists, ask the user to create a personal access token
   (Capsule → My Preferences → API Authentication Tokens) and save it to one of those places
   themselves, for example `! pbpaste > ~/.config/capsule/token && chmod 600 ~/.config/capsule/token`.
3. **Projects are `kases`.** Capsule renamed Cases to Projects but kept `/kases` paths and the
   `kase` body key. Contacts are `parties` (`type` `person` or `organisation`).
4. **Find before you change.** Look records up by id, search (`/{entity}/search?q=`) or filter
   (`/{entity}/filters/results`). Resolve names to ids from reference lists (users, milestones,
   stages, categories, tags, field definitions) rather than guessing.
5. **Send only what changes.** PUT updates only the fields sent; `null` clears a field; nested
   items (phones, emails, tags, custom field values…) are changed by `id` and removed with
   `{"id": N, "_delete": true}`. See [references/writing.md](references/writing.md).
6. **Check text before writing.** Fields have length limits (opportunity name 100, project
   name 255, most short fields 250, long text 8,000–16,000). Capsule can't store characters
   above U+FFFF, such as most emoji: it silently saves "��" or fails with a 500. Tell the user
   rather than changing their text. See [references/writing.md](references/writing.md#text-limits).
7. **Read leniently.** Any field can be missing or null, even names and nested ids. Don't let
   one odd record stop a report or script.
8. **Trust live responses over the docs.** Capsule's docs have been wrong or silent several
   times. When data looks missing or odd, check a live GET before guessing. The known traps are
   in [references/gotchas.md](references/gotchas.md); read it before writing sync or bulk code.

## Picking an approach

| The user wants… | Do this |
|---|---|
| One record by name, email, phone or postcode | `get {parties,opportunities,kases}/search -p q=…` |
| Records matching criteria (tag, owner, date, custom field, milestone…) | `post {entity}/filters/results` – see [references/filters.md](references/filters.md) |
| Everything, or everything changed since a time | `get {entity} --all -p since=2026-01-01T00:00:00Z` |
| Up to 10 known records at once | `get parties/1,2,3` (404 if any one is missing) |
| A record's history | `get parties/{id}/entries -p embed=party,creator,activityType` (add `-p includeLinked=true` for an organisation) |
| Open tasks | `get tasks --all -p embed=party,opportunity,kase,owner` |
| An opportunity's products | `get opportunities/{id} -p embed=lineItems -p sideload=true`, names and prices from `get products --all -p embed=prices -p sideload=true` |
| To add a note, task, track, contact, opportunity or project | Build the body from [references/writing.md](references/writing.md), show it, then send with `--confirm` |
| To build an app or integration | Read [references/oauth.md](references/oauth.md) and [references/gotchas.md](references/gotchas.md) |

The full endpoint list, with embeds and paging limits, is in
[references/endpoints.md](references/endpoints.md).

## Reading responses

- Lists come back under a plural key (`parties`, `opportunities`, `kases`, `tasks`, `entries`…);
  single records under the singular one (`party`, `kase`…).
- A contact's display name is `name` if not blank, else `firstName` + `lastName`.
- An opportunity is open without `closedOn`; closed ones are lost if they have a `lostReason` or
  their milestone is named "Lost", otherwise won. Use `lastOpenMilestone` for the stage a closed
  one reached.
- A project is closed when `status` is `CLOSED` (case-insensitive).
- Custom field values only carry the definition's id and name; get the type, options and DataTag
  from `/{entity}/fields/definitions`.
- Dates (`dueOn`, `expectedCloseOn`) are `YYYY-MM-DD` with no time zone; timestamps
  (`createdAt`, `updatedAt`) are ISO 8601 UTC with `Z`.

When reporting to the user, link records to the web app where helpful:
`https://<subdomain>.capsulecrm.com/party/<id>`, `/opportunity/<id>`, `/project/<id>`
(the subdomain comes from `whoami`).

## Errors

| Status | Meaning | What to do |
|---|---|---|
| 400 | Bad JSON or wrong root key | Check the wrapper (`party`, `opportunity`, `kase`, `task`, `entry`, `track`) |
| 401 | Token missing, wrong or expired | Ask the user for a fresh token |
| 403 | Token lacks scope (read-only) or the user isn't an admin | Tell the user; don't retry |
| 404 | No such record (or one of several ids) | Re-check ids; it may have been deleted |
| 422 | Validation failed, including text over a field's limit | Show Capsule's message (`message` + each `errors[].message`), fix the body |
| 500 on a write | Usually text with characters above U+FFFF (emoji) in an organisation name, title or email | Don't retry unchanged; ask the user to remove those characters |
| 429 | Over 4,000 requests/hour for this user | The client waits and retries up to 3 times; otherwise stop and report |
| 202 | Accepted for later (large deletes) | Poll the `Location` job URL (`/jobs/{id}`) |

Be gentle with bulk work: prefer `since`, filters and `--all` with `perPage=100` over fetching
records one by one, and pause about a second between requests in long loops.
