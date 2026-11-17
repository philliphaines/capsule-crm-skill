# Filters

`POST /api/v2/{parties|opportunities|kases}/filters/results` runs a structured query. It reads
data only, so it's safe to run without asking. `page`, `perPage` (max 100) and `embed` go in the
query string; the reply looks like that entity's list (`{"parties": [...]}`).

```json
{"filter": {
  "conditions": [
    {"field": "type", "operator": "is", "value": "person"},
    {"field": "addedOn", "operator": "is within last", "value": 30},
    {"orGroup": [
      {"field": "owner", "operator": "is", "value": 4},
      {"field": "owner", "operator": "is", "value": 7}
    ]}
  ],
  "orderBy": [{"field": "lastContactedOn", "direction": "ascending"}]
}}
```

Top-level conditions are ANDed; conditions inside an `orGroup` are ORed. `direction` is
`ascending` or `descending`.

```sh
python3 scripts/capsule.py post parties/filters/results --all -p embed=tags,fields --data @filter.json
```

## Operators

| Field type | Operators | Value |
|---|---|---|
| any | `is`, `is not` | same type as the field |
| string | `starts with`, `ends with`, `contains` | string |
| number | `is greater than`, `is less than` | number |
| date | `is after`, `is before` | `YYYY-MM-DD` |
| date | `is older than`, `is within last`, `is within next` | number of **days** |

## Contact fields (`parties`)

| Field | Type |
|---|---|
| `id`, `owner`, `team` | number (user and team ids) |
| `name`, `jobTitle`, `email`, `phone`, `city`, `zip`, `state` | string |
| `country` | string, e.g. `"US"`, `"GB"` |
| `type` | `"person"` or `"organisation"` |
| `tag` | tag id (number) or name (string) |
| `hasEmailAddress`, `hasPhoneNumber`, `hasAddress`, `hasPeople`, `hasTags` | boolean |
| `addedOn`, `updatedOn`, `lastContactedOn` | date |
| `custom:{fieldId}` | the custom field's type |
| `org.name`, `org.tag`, `org.custom:{fieldId}` | the person's organisation's name, tag or custom field |

## Opportunity fields (`opportunities`)

| Field | Type |
|---|---|
| `id`, `owner`, `team`, `probability` | number |
| `name`, `status`, `milestone`, `lostReason`, `currency`, `expectedValue` | string |
| `pipeline` | pipeline id (number) or name (string) |
| `tag` | tag id or name |
| `isOpen`, `isStale`, `isOwnedByMe`, `hasTags` | boolean |
| `addedOn`, `updatedOn`, `closedOn`, `expectedCloseOn` | date |
| `custom:{fieldId}` | the custom field's type |

## Project fields (`kases`)

| Field | Type |
|---|---|
| `id`, `owner`, `team` | number |
| `name`, `status` | string |
| `board`, `stage` | id (number) or name (string) |
| `tag` | tag id or name |
| `isOpen`, `isOwnedByMe`, `hasTags` | boolean |
| `addedOn`, `updatedOn`, `startOn`, `closedOn`, `expectedCloseOn` | date |
| `custom:{fieldId}` | the custom field's type |

## Tips

- Custom fields go by definition id: look it up in `/{entity}/fields/definitions` first.
- Prefer tag ids over names: they survive a rename.
- Owners are user ids from `/users`; "mine" is `/users/current`'s id (or `isOwnedByMe` for
  opportunities and projects).
- There's no task filter: list `/tasks` (with `status`) and filter locally.
- For "changed since", `GET /{entity}?since=…` is cheaper than an `updatedOn` filter and catches
  changes to the minute.
