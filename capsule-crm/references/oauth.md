# Authentication

## Personal access tokens

For scripts, internal tools and this skill. Create one in Capsule under **My Preferences → API
Authentication Tokens**. It acts as that user, with their permissions, until deleted. Send it as
`Authorization: Bearer <token>`. Treat it like a password: keep it out of code, logs and git.

## OAuth 2 (apps used by other people)

Register the app at `https://developer.capsulecrm.com/`. Server-side web apps get a `client_secret`; apps on users' devices (mobile, desktop, extensions) are registered as **installed** and use no secret, so use PKCE.

| Step | Endpoint |
|---|---|
| Authorise | `GET https://api.capsulecrm.com/oauth/authorise` |
| Exchange / refresh | `POST https://api.capsulecrm.com/oauth/token` |
| Revoke | `POST https://api.capsulecrm.com/oauth/token/revoke` (`/oauth/revoke` has also been seen to work) |

Scopes: `read`, `read write` (default), `read write user_preference`.

### Authorisation code with PKCE

1. Make a verifier from 32 random bytes, base64url without padding. The challenge is
   base64url(SHA-256(verifier)) without padding; method `S256`. Make `state` the same way.
2. Open in the system browser:
   `…/oauth/authorise?response_type=code&client_id=…&redirect_uri=…&scope=read%20write&state=…&code_challenge=…&code_challenge_method=S256`
3. On the redirect: fail on `error` (show `error_description`), fail if `state` doesn't match
   (never exchange the code), fail if `code` is empty.
4. `POST /oauth/token`, form-encoded: `grant_type=authorization_code`, `code`, `redirect_uri`,
   `client_id`, `code_verifier` (plus `client_secret` for web apps).
5. The reply has `access_token`, `refresh_token`, `expires_in` (about 7 days), `token_type`,
   `scope` and `subdomain`. Call `GET /api/v2/site` to name the account.

**Capsule accepts only `https` redirect URIs.** Custom schemes like `myapp://callback` are
rejected, so a native app needs a universal link / App Link on a domain you control (for
example `https://example.com/myapp/oauth/callback`, opened by the app via the platform's
verified link files). The redirect must match the registered one exactly.

### Keeping tokens fresh

- Treat a token as expired 60 seconds before `expires_in` runs out.
- Refresh with `POST /oauth/token`, form-encoded: `grant_type=refresh_token`, `refresh_token`,
  `client_id`. The reply may omit `refresh_token` or `scope`: keep the previous ones. If it
  includes a new refresh token, replace the old one.
- Run at most one refresh per account at a time; other requests wait for it.
- `400 {"error": "invalid_grant"}` from the token endpoint means the sign-in has ended. Delete
  the token and ask the user to sign in again.
- On a 401 from the API, refresh once and retry; a second 401 means sign in again.
- Only send writes if the granted `scope` (split on spaces) includes `write`; a write without it
  gets 403 `insufficient_scope`.

### Signing out

Revoke the refresh token (which also revokes its access tokens and removes the app from the
user's authorised applications), then the access token, best effort. Delete the stored tokens
first so a failed revoke can't leave the user signed in.

### Storage

Keep tokens in the platform's secure store (Keychain, Keystore-backed storage, a server-side
secret store), one entry per account. Never in the database, logs or backups.
