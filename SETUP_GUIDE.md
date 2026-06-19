# Google OAuth Setup - Quick Start Guide

## What Was Implemented

Complete Google OAuth 2.0 authentication system with:
- ✅ User login with Google (identity verification)
- ✅ Google Drive integration (browse and import files)
- ✅ JWT session management (8-hour expiration)
- ✅ Dialog-branded UI theme
- ✅ Protected routes
- ✅ User profile display in sidebar

## Prerequisites

1. **Google Cloud Project** with OAuth 2.0 credentials
2. **Node.js** and **Python 3.8+** installed
3. **AWS credentials** configured (for S3 and Bedrock)

---

## Step 1: Google Cloud Console Setup

### A. Create OAuth 2.0 Credentials

1. Go to: https://console.cloud.google.com/apis/credentials
2. Click **"+ CREATE CREDENTIALS"** → **OAuth client ID**
3. Select **Application type**: Web application
4. **Name**: Dialog BDA Pipeline
5. **Authorized JavaScript origins**:
   - `http://localhost:3000`
6. **Authorized redirect URIs**:
   - `http://localhost:3000/auth-callback`
   - `http://localhost:3000/google-callback`
7. Click **CREATE**
8. **Copy the Client ID and Client Secret**

### B. Configure OAuth Consent Screen

1. Go to: https://console.cloud.google.com/apis/credentials/consent
2. **User Type**: Internal (for testing) or External
3. Fill in required fields:
   - App name: Dialog BDA Pipeline
   - User support email: your-email@example.com
   - Developer contact: your-email@example.com
4. **Scopes**: Add the following:
   - `openid`
   - `.../auth/userinfo.email`
   - `.../auth/userinfo.profile`
   - `.../auth/drive.readonly`
5. **Test users** (if in Testing mode):
   - Add your email addresses

---

## Step 2: Backend Configuration

### A. Copy Environment File

```bash
cd backend/config
cp .env.example .env
```

### B. Edit `.env` File

```env
# AWS Credentials
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_key_here
AWS_SECRET_ACCESS_KEY=your_secret_here

# S3 and Bedrock
S3_RAW_BUCKET=your-bucket-name
BEDROCK_KB_ID=your-kb-id
BEDROCK_DATA_SOURCE_ID=your-datasource-id

# Google OAuth (FROM STEP 1)
GOOGLE_CLIENT_ID=your-google-client-id-here
GOOGLE_CLIENT_SECRET=your-google-client-secret-here

# JWT Configuration
JWT_SECRET=$(python -c "import secrets; print(secrets.token_hex(32))")
JWT_ALGORITHM=HS256
JWT_EXPIRE_HOURS=8
```

### C. Install Python Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### D. Start Backend Server

```bash
python api/app.py
```

Backend will run on: **http://localhost:8001**

---

## Step 3: Frontend Configuration

### A. Install Dependencies

```bash
cd frontend
npm install
```

Already includes:
- `jwt-decode` (for JWT handling)
- `axios` (for API calls)
- `react-router-dom` (for routing)

### B. Configure Environment (Optional)

If you need to change the API URL from the default (`http://localhost:8001`), create a `.env` file:

```bash
cd frontend
```

Create `.env`:

```env
REACT_APP_API_URL=http://localhost:8001
```

**Note**: The frontend URL (`http://localhost:3000`) is hardcoded in the backend for OAuth redirects.

### C. Start Frontend

```bash
npm start
```

Frontend will run on: **http://localhost:3000**

---

## Step 4: Test the System

### A. Login Flow

1. Open browser: **http://localhost:3000**
2. You'll be redirected to `/login` (not authenticated)
3. Click **"CONTINUE WITH GOOGLE"**
4. Google OAuth popup opens
5. Select your Google account
6. Grant permissions (all 4 scopes)
7. Popup closes automatically
8. You're redirected to `/upload` (authenticated)
9. Sidebar shows your profile picture and name

### B. Google Drive Browser

1. Navigate to **Upload** page
2. You should see a **Google Drive tab** (if GoogleDriveBrowser is integrated)
3. Select **My Drive** or **Shared Drives** dropdown
4. Browse folders with breadcrumb navigation
5. Select files with checkboxes
6. Click **Import Selected Files**
7. Files are downloaded from Drive → uploaded to S3 → indexed in Bedrock KB

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     AUTHENTICATION FLOW                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. User clicks "Continue with Google"                     │
│     Frontend: GET /api/auth/google-url                     │
│     Backend generates OAuth URL with 4 scopes              │
│                                                             │
│  2. OAuth popup opens → User consents                      │
│     Google redirects: /auth-callback?code=xxx&state=yyy    │
│                                                             │
│  3. AuthCallback.jsx:                                      │
│     GET /api/auth/callback?code=xxx&state=yyy              │
│     Backend exchanges code → tokens                        │
│     Backend fetches user info from Google                  │
│     Backend creates JWT with embedded drive_token          │
│     Returns { token, user }                                │
│                                                             │
│  4. Frontend stores token in localStorage                  │
│     AuthContext decodes JWT → extracts user + driveToken   │
│     Navigate to /upload                                    │
│                                                             │
│  5. Subsequent requests:                                   │
│     Authorization: Bearer {jwt_token}                      │
│     Backend validates JWT signature                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                   GOOGLE DRIVE IMPORT FLOW                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. GoogleDriveBrowser component loads                     │
│     GET /api/google-drive/shared-drives                    │
│     Lists all Shared Drives                                │
│                                                             │
│  2. User selects drive → browses folders                   │
│     GET /api/google-drive/browse?folder_id=xxx&drive_id=yyy│
│     Returns { folders: [...], files: [...] }              │
│                                                             │
│  3. User selects files → clicks Import                     │
│     POST /api/google-drive/import                          │
│     { files: [...], google_access_token, user_id }        │
│                                                             │
│  4. Backend for each file:                                 │
│     - Downloads from Google Drive API                      │
│     - Extracts metadata                                    │
│     - Uploads to S3 with metadata                          │
│     - Triggers Bedrock KB ingestion                        │
│                                                             │
│  5. Files queryable in ~1-2 minutes                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## File Structure

### Backend Files Created/Modified

```
backend/
├── api/
│   └── app.py                     # Added auth endpoints + browse endpoint
├── config/
│   ├── settings.py                # Added JWT + OAuth config
│   └── .env.example               # Updated with OAuth variables
├── services/
│   ├── auth_service.py            # NEW: JWT + OAuth handling
│   └── google_drive_service.py    # Added browse_folder() method
└── requirements.txt               # NEW: Added PyJWT, google-auth, etc.
```

### Frontend Files Created/Modified

```
frontend/
├── src/
│   ├── App.js                     # Protected routes + AuthProvider
│   ├── context/
│   │   └── AuthContext.jsx        # NEW: Global auth state
│   ├── components/
│   │   ├── Sidebar.jsx            # Shows user profile from JWT
│   │   └── GoogleDriveBrowser.jsx # NEW: Drive folder browser UI
│   └── pages/
│       ├── Login.jsx              # NEW: Dialog-branded login
│       ├── AuthCallback.jsx       # NEW: OAuth popup handler
│       ├── Upload.jsx             # Can integrate GoogleDriveBrowser
│       └── Retrieve.jsx           # Protected route
└── package.json                   # Added jwt-decode dependency
```

---

## Security Notes

### ⚠️ Current Implementation (Development)

1. **JWT in localStorage**: Vulnerable to XSS attacks
   - **Production fix**: Use httpOnly cookies

2. **Drive token embedded in JWT**: Expires after 1 hour, but JWT valid for 8 hours
   - **Production fix**: Implement token refresh endpoint

3. **Weak default JWT_SECRET**: Easy to guess
   - **Must change**: Generate with `python -c "import secrets; print(secrets.token_hex(32))"`

4. **In-memory state storage**: `oauth_states` dict
   - **Production fix**: Use Redis with TTL

5. **No rate limiting**: OAuth endpoints unprotected
   - **Production fix**: Add rate limiting middleware

### 🔒 Production Checklist

- [ ] Move JWT to httpOnly cookies
- [ ] Implement token refresh endpoint
- [ ] Generate strong JWT_SECRET (64 characters)
- [ ] Use Redis for OAuth state storage
- [ ] Add rate limiting (10 req/min per IP)
- [ ] Update OAuth URIs to production domain
- [ ] Submit app for Google verification
- [ ] Move credentials to AWS Secrets Manager
- [ ] Enable CORS for production domain only
- [ ] Add audit logging for all auth events

---

## Troubleshooting

### 1. `redirect_uri_mismatch`

**Problem**: OAuth redirect URI doesn't match Google Console

**Fix**:
- Go to Google Console → Credentials
- Add exact URI: `http://localhost:3000/auth-callback`
- Must match exactly (including trailing slash, http vs https, port)

### 2. `invalid_grant`

**Problem**: Authorization code expired or already used

**Causes**:
- React StrictMode causes double render → double exchange
- Code expired (10-minute validity)

**Fix**:
- Code checks `sessionStorage` to prevent double exchange
- If persists, restart backend

### 3. Popup blocked

**Problem**: Browser blocks OAuth popup

**Fix**:
- Allow popups for `localhost:3000`
- Check browser popup blocker settings

### 4. Drive token expired

**Problem**: User authenticated >1 hour ago, Drive features fail

**Fix**:
- Log out and sign in again
- Implement token refresh (production)

### 5. User not in test users

**Problem**: "This app is blocked" error

**Fix**:
- Add email to: Console → OAuth consent screen → Test users

---

## API Endpoints Reference

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/auth/google-url` | Generate OAuth consent URL |
| `GET` | `/api/auth/callback?code=&state=` | Exchange code for JWT |
| `GET` | `/api/auth/me` | Get current user from JWT |
| `POST` | `/api/auth/logout` | Logout (client-side confirmation) |

### Google Drive

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/google-drive/shared-drives` | List Shared Drives |
| `GET` | `/api/google-drive/browse` | Browse folder (folders + files) |
| `GET` | `/api/google-drive/files` | List files (flat) |
| `POST` | `/api/google-drive/import` | Import files to S3 + KB |

---

## Next Steps

### Immediate (Working System)

1. ✅ Test login flow end-to-end
2. ✅ Test Drive browser navigation
3. ✅ Test file import from Drive
4. ✅ Verify files indexed in Bedrock KB
5. ✅ Test query against imported files

### Integration (Upload Page)

To add Google Drive tab to Upload page:

```jsx
import GoogleDriveBrowser from '../components/GoogleDriveBrowser';

// In Upload.jsx, add a tab:
<Tab>Google Drive</Tab>

// In tab panel:
<GoogleDriveBrowser />
```

### Production Deployment

1. Update OAuth URIs in Google Console
2. Change JWT_SECRET to strong random value
3. Move to httpOnly cookies
4. Implement token refresh
5. Add Redis for state storage
6. Submit for Google app verification
7. Move to AWS Secrets Manager
8. Enable production CORS

---

## Support

For issues or questions:
- Check [GOOGLE_AUTH_SETUP.md](./GOOGLE_AUTH_SETUP.md) for detailed flow documentation
- Review backend logs: `python api/app.py` output
- Check frontend console: Browser DevTools → Console
- Verify .env files are correctly configured

---

**Implementation Complete! 🎉**

The system now has:
- ✅ Google OAuth login with Dialog branding
- ✅ JWT session management
- ✅ Protected routes
- ✅ User profile in sidebar
- ✅ Google Drive folder browser
- ✅ File import from Drive to S3 + Bedrock KB
