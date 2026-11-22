# capsule-crm skill

A Claude Code skill for the Capsule CRM REST API v2, built from live testing against Capsule
plus Capsule's developer docs.

> **Not an official Capsule product.** This is an independent project. Capsule doesn't
> endorse or support it.

```
capsule-crm/
  SKILL.md                 version (frontmatter), when to use it, rules (writes need approval), quick recipes
  CHANGELOG.md             what changed in each version
  scripts/capsule.py       stdlib-only client: token lookup, paging, 429 retries, write guard
  scripts/bump_version.py  bumps the version in SKILL.md and adds a CHANGELOG entry
  references/endpoints.md  every endpoint, embeds and paging limits
  references/writing.md    request bodies: contacts, tags, custom fields, opportunities, projects, tasks, tracks, notes
  references/filters.md    filters/results fields and operators
  references/gotchas.md    live-tested traps (Link header, /milestones, embed=opportunity, line items…)
  references/oauth.md      personal tokens, OAuth + PKCE, refresh, https-only redirects
```

Install for every project: `ln -s "$PWD/capsule-crm" ~/.claude/skills/capsule-crm`

Token: `$CAPSULE_API_TOKEN`, `$CAPSULE_TOKEN_FILE`, `.capsule-token` (cwd or a parent) or
`~/.config/capsule/token`.

## Versioning

Every change to the skill bumps `metadata.version` in `capsule-crm/SKILL.md`:

```sh
python3 capsule-crm/scripts/bump_version.py minor "Added X"   # or patch / major; --show prints it
```
