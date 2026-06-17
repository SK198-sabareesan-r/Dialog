# Google OAuth Setup — Login & Drive Integration

## Overview

This system uses Google OAuth 2.0 for two purposes:
1. **User authentication** — login with Google account (identity)
2. **Google Drive access** — browse and import files from personal Drive and Shared Drives

Both are handled in a **single sign-in** — the user authenticates once and gets both.

---

## Current Credentials

### Google Cloud Project

| Field | Value |
|---|---|
| Project Name | IGNITION |
| Project ID | `ignition-488710` |
| Console URL | https://console.cloud.google.com/apis/credentials?project=ignition-488710 |

### OAuth 2.0 Client (Web Application)

| Field | Value |
|---|---|
| Client Name | Web client 1 |
| Client Type | Web application |
| Client ID | Stored in `backend/.env` as `GOOGLE_CLIENT_ID` |
| Client Secret | Stored in `backend/.env` as `GOOGLE_CLIENT_SECRET` |
| Creation Date | June 17, 2026 |

### Authorized URIs

| Type | URI |
|---|---|
| JavaScript Origin | `http://localhost:3000` |
| Redirect URI 1 | `http://localhost:3000/google-callback` (Drive access) |
| Redirect URI 2 | `http://localhost:3000/auth-callback` (Login) |

> ⚠️ When deploying to production, add your production domain URIs here.

---

## Environment Variables

These go in `backend/.env`:

```env
# Google OAuth — Web application client
GOOGLE_CLIENT_ID=your-google-client-id-here
GOOGLE_CLIENT_SECRET=your-google-client-secret-here

# JWT session config
JWT_SECRET=dialog-bda-pipeline-secret-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRE_HOURS=8
```

> ⚠️ Change `JWT_SECRET` to a strong random string in production.  
> Generate one with: `python -c "import secrets; print(secrets.token_hex(32))"`

---

## OAuth Scopes Requested

When a user signs in, the app requests these Google scopes in one consent screen:

| Scope | Purpose |
|---|---|
| `openid` | Verify user identity |
| `userinfo.email` | Get email address |
| `userinfo.profile` | Get name and profile picture |
| `drive.readonly` | Browse and download files from Drive |

The user sees this once. After consent, the `drive_token` is embedded in the JWT and reused automatically — **no second sign-in needed for Drive access**.

---

## Authentication Flow (Step by Step)

```
┌─────────────────────────────────────────────────────────────────────┐
│                        LOGIN FLOW                                   │
│                                                                     │
│  1. User visits http://localhost:3000                               │
│     → Not authenticated → redirected to /login                     │
│                                                                     │
│  2. User clicks "Continue with Google"                              │
│     → Frontend: GET /api/auth/google-url                           │
│     → Backend generates consent URL with all 4 scopes              │
│     → Popup opens: accounts.google.com/o/oauth2/auth               │
│                                                                     │
│  3. User selects account + clicks Allow                             │
│     → Google redirects popup to:                                    │
│        http://localhost:3000/auth-callback?code=xxx&state=yyy       │
│                                                                     │
│  4. AuthCallback.jsx calls:                                         │
│     GET /api/auth/callback?code=xxx&state=yyy                       │
│     → Backend exchanges code for tokens (Google OAuth token URI)   │
│     → Backend calls: GET https://googleapis.com/oauth2/v2/userinfo │
│     → Gets: { id, email, name, picture }                           │
│     → Creates JWT payload:                                          │
│        {                                                            │
│          sub: "google_user_id",                                     │
│          email: "user@gmail.com",                                   │
│          name: "Mohammed Anes",                                     │
│          picture: "https://...",                                    │
│          drive_token: "ya29.xxx",   ← Drive access token          │
│          exp: 1234567890            ← 8 hours from now             │
│        }                                                            │
│     → Signs JWT with JWT_SECRET                                     │
│     → Returns { token, user }                                       │
│                                                                     │
│  5. AuthCallback.jsx posts token to parent window (postMessage)    │
│     → Popup closes                                                  │
│     → Login.jsx stores token in localStorage                        │
│     → User redirected to Dashboard                                  │
│                                                                     │
│  6. Sidebar shows: profile picture, name, email                    │
│     Session lasts 8 hours (configurable via JWT_EXPIRE_HOURS)      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Google Drive Import Flow (Step by Step)

```
┌─────────────────────────────────────────────────────────────────────┐
│                     DRIVE IMPORT FLOW                               │
│                                                                     │
│  Prerequisites: User is logged in (drive_token available in JWT)   │
│                                                                     │
│  1. User opens Upload → Google Drive tab                           │
│     → drive_token extracted from AuthContext                        │
│     → Shows "Google Drive connected — user@gmail.com"              │
│                                                                     │
│  2. Page loads shared drives:                                       │
│     GET /api/google-drive/shared-drives                             │
│        ?google_access_token={drive_token}                           │
│     → Lists all Team Drives / Shared Drives user has access to     │
│                                                                     │
│  3. User selects a drive (or stays on My Drive)                    │
│     → Page auto-browses root folder:                                │
│        GET /api/google-drive/browse                                 │
│           ?google_access_token={drive_token}                        │
│           &folder_id=root                                           │
│           &drive_id={selected_drive_id}   ← optional              │
│     → Returns { folders: [...], files: [...] }                     │
│                                                                     │
│  4. User navigates folders (breadcrumb navigation)                 │
│     → Each click: GET /api/google-drive/browse?folder_id={id}      │
│     → Breadcrumb updates: My Drive > HR > Policies                 │
│                                                                     │
│  5. User selects files (checkboxes) → clicks Import                │
│     POST /api/google-drive/import                                   │
│     {                                                               │
│       files: [{id, name, mimeType}, ...],                          │
│       google_access_token: "ya29.xxx",                              │
│       user_id: "user@email.com",                                   │
│       team_id: "team456",     ← optional                          │
│       drive_id: "xxx"         ← optional, for Shared Drives       │
│     }                                                               │
│                                                                     │
│  6. Backend for each file:                                         │
│     a. Downloads bytes from Google Drive API                        │
│     b. Extracts metadata (author, dates, EXIF, etc.)               │
│     c. PUTs to S3: users/{user_id}/{date}/{filename}               │
│        with metadata headers: user_id, source=google_drive, etc.   │
│     d. Triggers Bedrock KB ingestion job                           │
│                                                                     │
│  7. File queryable in ~1-2 minutes                                 │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Backend API Endpoints

### Authentication

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/auth/google-url` | Generate Google consent URL (login flow) |
| `GET` | `/api/auth/callback?code=&state=` | Exchange code → JWT token |
| `GET` | `/api/auth/me` | Get current user info from JWT |
| `POST` | `/api/auth/logout` | Client-side logout confirmation |

### Google Drive

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/google-drive/shared-drives` | List all Shared Drives user has access to |
| `GET` | `/api/google-drive/browse` | Browse folder contents (folders + files) |
| `GET` | `/api/google-drive/files` | List files (flat, no folder navigation) |
| `POST` | `/api/google-drive/import` | Download from Drive + upload to S3 + sync KB |
| `GET` | `/api/google-drive/auth-url` | Generate Drive-only OAuth URL (legacy) |
| `GET` | `/api/google-drive/callback` | Drive-only OAuth callback (legacy) |

---

## Test Users (OAuth Consent Screen)

Since the app is in **Testing** mode, only explicitly listed emails can sign in.

**Current test users:**
- `mohammed.a@shellkode.com`
- `mohammedanes008@gmail.com`
- `roshini.r@shellkode.com`

**To add more users:**
> Google Cloud Console → APIs & Services → OAuth consent screen → Audience → Test users → + Add users

**To make public (production):**
> OAuth consent screen → Publishing status → Publish App  
> Note: Requires Google verification for sensitive scopes like `drive.readonly`

---

## Files

| File | Purpose |
|---|---|
| `backend/.env` | Live credentials (never commit to git) |
| `backend/config/.env.example` | Template with placeholder values |
| `backend/config/settings.py` | Loads env vars into Python Settings class |
| `backend/api/app.py` | Auth + Drive API endpoints |
| `frontend/src/context/AuthContext.jsx` | JWT storage + driveToken exposure |
| `frontend/src/pages/Login.jsx` | Login page with Google button |
| `frontend/src/pages/AuthCallback.jsx` | OAuth popup handler for login |
| `frontend/src/pages/GoogleCallback.jsx` | OAuth popup handler for Drive |
| `frontend/src/pages/Upload.jsx` | Upload UI with Drive browser |

---

## Production Checklist

When moving to production, update these:

- [ ] Add production domain to **Authorized JavaScript origins**  
      e.g. `https://bda.dialog.lk`
- [ ] Add production callback URLs to **Authorized redirect URIs**  
      e.g. `https://bda.dialog.lk/auth-callback`  
      e.g. `https://bda.dialog.lk/google-callback`
- [ ] Change `JWT_SECRET` to a strong random secret
- [ ] Set `JWT_EXPIRE_HOURS` appropriately (e.g. 8 for workday)
- [ ] Submit app for Google verification (for drive.readonly scope)
- [ ] Move from Testing to Production in OAuth consent screen
- [ ] Use AWS Secrets Manager instead of `.env` file for credentials
- [ ] Enable `USE_EVENTBRIDGE=true` and set up EventBridge for scheduled sync

---

## Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `redirect_uri_mismatch` | URI in Google Console doesn't match backend | Add exact URI to Console redirect URIs |
| `invalid_grant` | Auth code expired or used twice | Sign in again; check for double render (StrictMode) |
| `Scope has changed` | `include_granted_scopes` merging old scopes | Removed — `OAUTHLIB_RELAX_TOKEN_SCOPE=1` set |
| `Something went wrong` | User not in test users list | Add email to OAuth consent screen test users |
| Drive tab shows "not available" | Logged in before drive scope was added | Log out and sign in again |
| 404 on `/api/auth/google-url` | Old backend process running | Kill all python.exe, restart backend |
