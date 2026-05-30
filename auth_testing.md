# Auth-Gated App Testing Playbook (Emergent Google OAuth)

## Step 1: Create Test User & Session

```bash
mongosh --eval "
use('test_database');
var userId = 'test-user-' + Date.now();
var sessionToken = 'test_session_' + Date.now();
db.users.insertOne({
  user_id: userId,
  email: 'test.user.' + Date.now() + '@example.com',
  name: 'Test Admin',
  picture: 'https://via.placeholder.com/150',
  role: 'admin',
  created_at: new Date()
});
db.user_sessions.insertOne({
  user_id: userId,
  session_token: sessionToken,
  expires_at: new Date(Date.now() + 7*24*60*60*1000),
  created_at: new Date()
});
print('Session token: ' + sessionToken);
print('User ID: ' + userId);
"
```

## Step 2: Test Backend API

```bash
# Test auth endpoint
curl -X GET "$REACT_APP_BACKEND_URL/api/auth/me" \
  -H "Authorization: Bearer YOUR_SESSION_TOKEN"

# Test protected admin endpoints
curl -X GET "$REACT_APP_BACKEND_URL/api/admin/businesses" \
  -H "Authorization: Bearer YOUR_SESSION_TOKEN"
```

## Step 3: Browser Testing

```javascript
await page.context.add_cookies([{
    "name": "session_token",
    "value": "YOUR_SESSION_TOKEN",
    "domain": "your-app.com",
    "path": "/",
    "httpOnly": true,
    "secure": true,
    "sameSite": "None"
}]);
await page.goto("https://your-app.com/admin");
```

## Allowlist behavior
- All Google accounts can sign in, BUT only emails in `ADMIN_EMAILS` env var (comma-separated) get `role=admin` and access to /admin.
- If `ADMIN_EMAILS` is empty, the FIRST user to sign in becomes admin (bootstrap mode).

## Checklist
- [ ] User document has `user_id` field
- [ ] Session `user_id` matches user's `user_id` exactly
- [ ] All queries use `{"_id": 0}` projection
- [ ] /api/auth/me returns user data
- [ ] /admin loads without redirect
- [ ] Non-admin users get 403 on /api/admin/*
