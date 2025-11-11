# Azure AD Setup Guide for OneNote RAG

This guide walks you through configuring Microsoft Entra ID (Azure AD) for user-delegated authentication with your OneNote RAG application.

## Overview

The application now uses **user-delegated authentication** where:
- Each user signs in with their Microsoft account
- Users can only access their own OneNote notebooks
- Tokens are managed securely with automatic refresh
- No client secrets or manual tokens needed

## Prerequisites

- An Azure account with access to Azure Active Directory (Entra ID)
- A Microsoft 365 account with OneNote notebooks
- Permission to register applications in your Azure AD tenant

## Step 1: Create Azure AD App Registration

1. Go to the [Azure Portal](https://portal.azure.com)
2. Navigate to **Azure Active Directory** → **App registrations**
3. Click **New registration**
4. Fill in the details:
   - **Name**: `OneNote RAG Application` (or your preferred name)
   - **Supported account types**: Choose based on your needs:
     - **Single tenant**: Only users in your organization
     - **Multi-tenant**: Users from any organization
     - **Personal Microsoft accounts**: Allow personal Microsoft accounts
   - **Redirect URI**: Leave blank for now (we'll add it next)
5. Click **Register**

## Step 2: Configure Platform Settings

After registration:

1. In your app registration, go to **Authentication** in the left sidebar
2. Click **Add a platform**
3. Select **Single-page application**
4. Add the redirect URI:
   ```
   http://localhost:5173/auth/callback
   ```

   For production, also add:
   ```
   https://your-domain.com/auth/callback
   ```

5. Under **Implicit grant and hybrid flows**, ensure these are **NOT** checked:
   - ☐ Access tokens
   - ☐ ID tokens

   (We're using Authorization Code Flow with PKCE, which is more secure)

6. Click **Configure**

## Step 3: Configure API Permissions

1. Go to **API permissions** in the left sidebar
2. Click **Add a permission**
3. Select **Microsoft Graph**
4. Select **Delegated permissions**
5. Add these permissions:
   - `User.Read` - Read user profile (basic info)
   - `Notes.Read` - Read user's OneNote notebooks
   - `Notes.Read.All` - Read all notebooks the user has access to
6. Click **Add permissions**
7. **(Optional)** Click **Grant admin consent for [Your Organization]** if you have admin rights
   - This pre-approves permissions for all users in your organization
   - If you don't have admin rights, users will see a consent screen on first login

## Step 4: Get Your Configuration Values

1. Go to **Overview** in your app registration
2. Copy these values:
   - **Application (client) ID** - You'll need this
   - **Directory (tenant) ID** - You'll need this

## Step 5: Configure Backend Environment

1. In your project, navigate to `backend/`
2. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

3. Edit `.env` and update these values:
   ```env
   MICROSOFT_CLIENT_ID=your_client_id_here
   MICROSOFT_TENANT_ID=your_tenant_id_here
   OAUTH_REDIRECT_URI=http://localhost:5173/auth/callback
   OAUTH_SCOPES=User.Read Notes.Read Notes.Read.All
   ```

4. **Remove or leave empty** (these are no longer used):
   - ~~MICROSOFT_CLIENT_SECRET~~ - Not needed for delegated auth
   - ~~MICROSOFT_GRAPH_TOKEN~~ - Not needed for delegated auth

## Step 6: Install Dependencies

### Backend
```bash
cd backend
pip install -r requirements.txt
```

This will install the new JWT authentication dependencies:
- `PyJWT` - JWT token validation
- `python-jose` - Enhanced JWT handling

### Frontend
```bash
cd frontend
npm install
```

All required dependencies are already in `package.json`.

## Step 7: Start the Application

### Backend
```bash
cd backend
python main.py
# or
uvicorn main:app --reload
```

The backend will start on `http://localhost:8000`

### Frontend
```bash
cd frontend
npm run dev
```

The frontend will start on `http://localhost:5173`

## Step 8: Test Authentication

1. Open your browser to `http://localhost:5173`
2. You should be redirected to the login page
3. Click **Sign in with Microsoft**
4. You'll be redirected to Microsoft's login page
5. Sign in with your Microsoft account
6. **First-time users**: Consent screen will appear asking to grant permissions
   - Review the permissions
   - Click **Accept**
7. You'll be redirected back to the application
8. You should now be logged in and see your email in the header

## Architecture Overview

### Authentication Flow

```
┌─────────┐                 ┌──────────┐                ┌──────────┐
│ User    │                 │ Frontend │                │ Backend  │
└────┬────┘                 └────┬─────┘                └────┬─────┘
     │                           │                           │
     │ 1. Click "Sign In"        │                           │
     │─────────────────────────>│                           │
     │                           │                           │
     │                           │ 2. GET /api/auth/login    │
     │                           │─────────────────────────>│
     │                           │                           │
     │                           │ 3. Return OAuth URL       │
     │                           │<─────────────────────────│
     │                           │                           │
     │ 4. Redirect to Microsoft OAuth                        │
     │<──────────────────────────│                           │
     │                                                       │
     ├──────────────────────────────────────────────────────┤
     │            Microsoft Login & Consent                  │
     ├──────────────────────────────────────────────────────┤
     │                                                       │
     │ 5. Redirect to /auth/callback?code=...               │
     │─────────────────────────>│                           │
     │                           │                           │
     │                           │ 6. POST /api/auth/callback│
     │                           │   with code               │
     │                           │─────────────────────────>│
     │                           │                           │
     │                           │                           │
     │                           │ 7. Exchange code for      │
     │                           │    access + refresh token │
     │                           │    Store tokens           │
     │                           │    Return session token   │
     │                           │<─────────────────────────│
     │                           │                           │
     │                           │ Store token in localStorage
     │                           │                           │
     │ 8. Redirect to /query     │                           │
     │<──────────────────────────│                           │
     │                                                       │
     │ 9. Make API requests with Bearer token               │
     │                           │─────────────────────────>│
     │                           │                           │
     │                           │ 10. Validate token        │
     │                           │     Return user's data    │
     │                           │<─────────────────────────│
```

### Token Management

- **ID Token**: Stored in frontend localStorage, sent as Bearer token
- **Access Token**: Stored in backend token store, used for Microsoft Graph API
- **Refresh Token**: Stored in backend token store, used to refresh expired access tokens
- **Automatic Refresh**: Middleware automatically refreshes tokens when they expire

### Per-User Data Isolation

- Each user's OneNote service is created with their own access token
- Users can only access notebooks they have permissions for
- Vector store can be enhanced with `user_id` filtering (optional)

## Troubleshooting

### "Authentication service not configured"
- Ensure `MICROSOFT_CLIENT_ID` and `MICROSOFT_TENANT_ID` are set in backend `.env`
- Restart the backend after changing `.env`

### "Invalid token" or 401 errors
- Check that your Azure AD app permissions are granted
- Ensure redirect URI matches exactly (including protocol and port)
- Clear browser localStorage and try logging in again

### "Insufficient permissions" or 403 errors
- Verify API permissions are added in Azure AD
- Grant admin consent if needed
- User may need to re-authenticate after permission changes

### Redirect URI mismatch
- Azure AD redirect URIs are case-sensitive
- Must match exactly: `http://localhost:5173/auth/callback`
- For production, update to your domain

### Token refresh fails
- Refresh tokens expire after 90 days of inactivity (Microsoft default)
- Users will need to sign in again
- This is normal and expected behavior

## Security Best Practices

✅ **Implemented**:
- Authorization Code Flow with PKCE (no client secret exposed)
- JWT token validation with Microsoft's signing keys
- Token encryption in backend storage
- CSRF protection with state parameter
- Automatic token refresh
- HTTP-only session management

⚠️ **Production Recommendations**:
1. Use HTTPS for all production deployments
2. Update CORS settings to only allow your production domain
3. Consider using Redis for token storage (scalability)
4. Implement rate limiting on auth endpoints
5. Set up monitoring for failed auth attempts
6. Use Azure AD Premium for advanced security features

## Production Deployment

### Frontend
1. Update `.env.production`:
   ```env
   VITE_API_URL=https://api.your-domain.com/api
   ```

2. Build:
   ```bash
   npm run build
   ```

### Backend
1. Update `.env`:
   ```env
   OAUTH_REDIRECT_URI=https://your-domain.com/auth/callback
   ```

2. Update Azure AD redirect URIs to include production URL

3. Consider environment-specific configurations

### Azure AD App Registration
1. Add production redirect URI
2. Update app settings for production (if needed)
3. Review and update API permissions

## Additional Resources

- [Microsoft Identity Platform Documentation](https://docs.microsoft.com/en-us/azure/active-directory/develop/)
- [Microsoft Graph API OneNote Documentation](https://docs.microsoft.com/en-us/graph/api/resources/onenote)
- [OAuth 2.0 Authorization Code Flow](https://oauth.net/2/grant-types/authorization-code/)
- [Azure AD Best Practices](https://docs.microsoft.com/en-us/azure/active-directory/develop/identity-platform-integration-checklist)

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review Azure AD app configuration
3. Check browser console and backend logs
4. Ensure all prerequisites are met
