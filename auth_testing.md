# Emergent Google Auth — Testing Playbook (CoolPet)

## Setup
- Backend receives session via `POST /api/auth/google/session` with `{session_id}` body
- Backend fetches user from `https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data`
- Stores `user_sessions` doc (7-day expiry) and sets `session_token` httpOnly cookie
- `get_current_user` in `server.py` checks cookie first, then falls back to legacy JWT Bearer

## Step 1: Create test session in Mongo
```bash
mongosh --eval "
use('test_database');
var userId = 'test-google-user-' + Date.now();
var sessionToken = 'test_session_' + Date.now();
db.users.insertOne({
  id: userId,
  email: 'test.google.' + Date.now() + '@example.com',
  name: 'Google Test User',
  picture: 'https://via.placeholder.com/150',
  provider: 'google',
  plan: 'free',
  created_at: new Date().toISOString()
});
db.user_sessions.insertOne({
  user_id: userId,
  session_token: sessionToken,
  expires_at: new Date(Date.now() + 7*24*60*60*1000).toISOString(),
  created_at: new Date().toISOString()
});
print('Session token: ' + sessionToken);
print('User ID: ' + userId);
"
```

## Step 2: Test backend API with session_token cookie
```bash
API=https://omni-iot-dash.preview.emergentagent.com
# Via cookie
curl -s "$API/api/auth/me" --cookie "session_token=YOUR_SESSION_TOKEN"

# Existing JWT flow must still work:
TOKEN=$(curl -s -X POST $API/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"ada@coolpet.io","password":"secret123"}' \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['token'])")
curl -s "$API/api/auth/me" -H "Authorization: Bearer $TOKEN"

# Protected endpoint via cookie
curl -s "$API/api/pets" --cookie "session_token=YOUR_SESSION_TOKEN"
```

## Step 3: Browser testing
```python
await page.context.add_cookies([{
    "name": "session_token",
    "value": "YOUR_SESSION_TOKEN",
    "domain": "omni-iot-dash.preview.emergentagent.com",
    "path": "/",
    "httpOnly": True,
    "secure": True,
    "sameSite": "None",
}])
await page.goto("https://omni-iot-dash.preview.emergentagent.com/dashboard")
```

## Checklist
- [ ] `POST /api/auth/google/session` upserts user by email, sets cookie, returns user object
- [ ] `GET /api/auth/me` returns 200 with a valid `session_token` cookie
- [ ] `GET /api/auth/me` returns 200 with a valid JWT Bearer (legacy flow)
- [ ] `GET /api/auth/me` returns 401 with no cookie/no bearer
- [ ] `POST /api/auth/logout` deletes session doc and clears cookie
- [ ] Protected routes (`/api/pets`, `/api/breaches`) accept both cookie and Bearer
- [ ] Signing in via Google button on Login/Signup pages navigates to `https://auth.emergentagent.com/?redirect=<origin>/dashboard`
- [ ] Return trip with `#session_id=...` is picked up by AuthCallback and lands the user on `/dashboard`
- [ ] Existing email+password signup/login still works

## Failure indicators
- ❌ /api/auth/me returns 401 after successful Google callback → check CORS `allow_credentials=True` + specific `allow_origins` (not `*`)
- ❌ Cookie missing in browser DevTools → check `secure=True, samesite=None, httponly=True`
- ❌ Callback hash not detected → routing uses `useLocation().hash`, not `window.location.hash`
