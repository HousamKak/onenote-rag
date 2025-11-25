# OneNote RAG - Notebook Selection & Shared Notebook Support Implementation

## ✅ Implementation Complete

This document provides a comprehensive guide for testing the newly implemented notebook selection and shared notebook access features.

---

## 📋 What Was Implemented

### Backend Features

#### 1. **Notebook Model** (`backend/models/notebook.py`)
- `Notebook` - Complete notebook model with:
  - `site_id` - SharePoint site ID for site-scoped API access
  - `is_shared` - Flag for shared notebooks
  - `user_role` - User's permission level (Owner/Contributor/Reader)
  - `is_selected` - User preference for sync inclusion
- `NotebookCandidate`, `NormalizedNotebook`, `NotebookStatus` - Supporting models

#### 2. **OneNoteDiscoveryService** (`backend/services/onenote_discovery_service.py`)
- Discovers notebooks from 3 sources:
  - **Owned notebooks**: `/me/onenote/notebooks`
  - **Recent notebooks**: `/me/onenote/notebooks/getRecentNotebooks`
  - **Shared notebooks**: `/me/drive/sharedWithMe` (filtered for OneNote)
- **Key Innovation**: Uses `getNotebookFromWebUrl` to normalize ALL notebooks
  - Extracts `site_id` from self URL
  - Enables unified site-scoped API access for owned + shared notebooks

#### 3. **Site-Scoped OneNote API Endpoints** (`backend/services/onenote_service.py`)
- `list_sections_site_scoped(site_id, notebook_id)`
- `list_pages_site_scoped(site_id, section_id)`
- `get_page_content_site_scoped(site_id, page_id)`
- **Backward Compatible**: Falls back to user-scoped endpoints if site_id not provided

#### 4. **Notebook Database** (`backend/services/notebook_db.py`)
- SQLite database for notebook metadata and preferences
- Migration: `backend/migrations/002_create_notebooks_schema.sql`
- Operations:
  - `upsert_notebook()` - Store/update discovered notebooks
  - `update_selection()` - Manage user's sync preferences
  - `get_notebooks_for_user()` - Retrieve selected notebooks
  - `update_sync_status()` - Track sync state per notebook

#### 5. **API Endpoints** (`backend/api/notebook_routes.py`)
- `GET /api/notebooks/discover` - Discover all accessible notebooks
- `POST /api/notebooks/select` - Update notebook selection
- `GET /api/notebooks/status` - Get sync status
- `GET /api/notebooks/list` - List notebooks from DB

#### 6. **Updated SyncOrchestrator** (`backend/services/sync_orchestrator.py`)
- `_get_notebooks_to_sync()` - Reads selected notebooks from NotebookDB
- Uses site-scoped endpoints for all notebooks (owned + shared)
- Updates notebook sync status in real-time
- **Backward Compatible**: Falls back to API discovery if NotebookDB unavailable

---

### Frontend Features

#### 1. **Updated Types** (`frontend/src/types/index.ts`)
- Extended `Notebook` interface with shared notebook fields
- `NotebookDiscoveryResponse` - Discovery API response
- `NotebookStatus` - Sync status tracking

#### 2. **API Client** (`frontend/src/api/client.ts`)
```typescript
notebookApi.discover()      // Discover notebooks
notebookApi.select(ids)     // Update selection
notebookApi.getStatus()     // Get sync status
notebookApi.list()          // List notebooks
```

#### 3. **UI Components** (`frontend/src/components/NotebookSelector/`)

**NotebookCard**
- Checkbox selection
- Shared badge with owner name
- User role badge (Owner/Contributor/Reader)
- External link to OneNote web

**NotebookList**
- Tabbed interface:
  - "My Notebooks" tab
  - "Shared with Me" tab
- Scrollable list with empty states

**NotebookSelector**
- Modal dialog for notebook management
- Discovery flow with loading states
- Error handling with retry
- Selection count display
- Save/Cancel actions

#### 4. **Settings Page Integration**
- "📚 Notebook Management" section
- "Manage Notebooks" button
- Success messages after selection

---

## 🧪 Testing Guide

### Prerequisites

1. **Microsoft Account with OneNote**
   - At least one owned notebook
   - (Optional) Access to a shared notebook for full testing

2. **Azure AD App Registration**
   - Required permissions:
     - `Notes.Read` - Access OneNote notebooks
     - `Files.Read.All` - Access shared files
     - `Sites.Read.All` - Access SharePoint sites (for shared notebooks)
     - `User.Read` - Read user profile

3. **Backend Configuration** (`.env` or Settings DB)
   ```env
   MICROSOFT_CLIENT_ID=your_client_id
   MICROSOFT_CLIENT_SECRET=your_secret
   MICROSOFT_TENANT_ID=your_tenant_id
   OAUTH_REDIRECT_URI=http://localhost:5173/auth/callback
   OAUTH_SCOPES=User.Read Files.Read.All Notes.Read Sites.Read.All offline_access openid profile
   ```

---

### Test Scenario 1: Notebook Discovery

**Objective**: Verify that the system discovers owned and shared notebooks.

#### Steps:

1. **Start the application**
   ```bash
   # Terminal 1 - Backend
   cd backend
   python main.py

   # Terminal 2 - Frontend
   cd frontend
   npm run dev
   ```

2. **Login**
   - Navigate to `http://localhost:5173`
   - Click "Login with Microsoft"
   - Authenticate with your Microsoft account

3. **Open Notebook Selector**
   - Go to Settings page
   - Scroll to "📚 Notebook Management"
   - Click "Manage Notebooks" button

4. **Verify Discovery**
   - ✅ Loading spinner appears
   - ✅ Notebooks are displayed
   - ✅ "My Notebooks" tab shows owned notebooks
   - ✅ "Shared with Me" tab shows shared notebooks (if any)
   - ✅ Each notebook shows:
     - Display name
     - Shared badge (if applicable) with owner name
     - User role badge
     - External link icon

#### Expected Results:

**Console Logs (Backend)**:
```
INFO - Discovering notebooks for user user-xxx
INFO - Discovering owned notebooks...
INFO - Found 3 owned notebooks
INFO - Discovering recent notebooks...
INFO - Found 2 recent notebooks
INFO - Discovering shared notebooks...
INFO - Found 1 shared notebooks
INFO - Total unique notebooks discovered: 4
INFO - Normalizing: Personal Notes (source: owned)
INFO - Normalized notebook: Personal Notes (id=xxx, site_id=xxx, shared=False)
...
```

**Frontend**:
- All notebooks visible with correct metadata
- Checkboxes reflect current selection state (all selected by default on first discovery)

---

### Test Scenario 2: Notebook Selection

**Objective**: Test selecting/deselecting notebooks for sync.

#### Steps:

1. **Open Notebook Selector** (from Settings)

2. **Toggle Selection**
   - Uncheck 1-2 notebooks
   - Check/uncheck several notebooks
   - Verify selection count updates at bottom

3. **Save Selection**
   - Click "Sync X Notebooks" button
   - Wait for success message

4. **Verify Persistence**
   - Close dialog
   - Reopen "Manage Notebooks"
   - ✅ Previous selection is preserved

#### Expected Results:

**Console Logs (Backend)**:
```
INFO - Updating notebook selection for user user-xxx: 2 notebooks
INFO - Updated selection for user user-xxx: 2 notebooks selected
```

**Frontend**:
- Success message: "Successfully selected 2 notebook(s). You can now sync them."
- Selection persists across dialog open/close

---

### Test Scenario 3: Syncing Selected Notebooks

**Objective**: Verify sync respects notebook selection and works with shared notebooks.

#### Steps:

1. **Select Notebooks**
   - Choose 1 owned and 1 shared notebook
   - Save selection

2. **Trigger Sync**
   - Go to Data Source page
   - Click "Sync Now" or "Full Sync"
   - Monitor sync progress

3. **Verify Sync**
   - ✅ Only selected notebooks are synced
   - ✅ Shared notebooks sync successfully
   - ✅ Progress shows correct notebook count

#### Expected Results:

**Console Logs (Backend)**:
```
INFO - Syncing 2 notebook(s)
INFO - Processing notebook: Personal Notes (shared=False)
INFO - Found 3 sections in notebook xxx (site-scoped)
INFO - Processing notebook: Team Notebook (shared=True)
INFO - Found 5 sections in notebook yyy (site-scoped)
INFO - Retrieved content for page zzz (2500 chars) (site-scoped)
...
```

**Success Indicators**:
- Sync completes without errors
- Both owned and shared notebook content appears in vector DB
- Query responses include content from both notebook types

---

### Test Scenario 4: Site-Scoped API Access

**Objective**: Confirm site-scoped endpoints work for shared notebooks.

#### Steps:

1. **Enable Debug Logging** (optional)
   ```python
   # backend/main.py
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **Sync Shared Notebook**
   - Select only a shared notebook
   - Run sync

3. **Monitor API Calls**
   - Check logs for site-scoped endpoint usage

#### Expected Results:

**Console Logs**:
```
DEBUG - Using site-scoped endpoint: /sites/{site_id}/onenote/notebooks/{notebook_id}/sections
DEBUG - Using site-scoped endpoint: /sites/{site_id}/onenote/sections/{section_id}/pages
DEBUG - Using site-scoped endpoint: /sites/{site_id}/onenote/pages/{page_id}/content
```

**No Errors**:
- ✅ No 403 Forbidden errors
- ✅ No 404 Not Found errors
- ✅ Content successfully retrieved

---

### Test Scenario 5: Notebook Status Tracking

**Objective**: Verify sync status is tracked per notebook.

#### Steps:

1. **Check Status API**
   ```bash
   curl -H "Authorization: Bearer YOUR_TOKEN" \
        http://localhost:8000/api/notebooks/status
   ```

2. **Verify Response**
   ```json
   {
     "notebooks": [
       {
         "id": "notebook-1",
         "displayName": "Personal Notes",
         "isSelected": true,
         "syncStatus": "completed",
         "lastSyncedAt": "2025-11-25T10:30:00Z",
         "pageCount": 42,
         "sectionCount": 5,
         "errorMessage": null
       },
       ...
     ]
   }
   ```

3. **Test Sync States**
   - Before sync: `syncStatus: "never_synced"`
   - During sync: `syncStatus: "syncing"`
   - After sync: `syncStatus: "completed"`
   - On error: `syncStatus: "error"` with `errorMessage`

---

### Test Scenario 6: Backward Compatibility

**Objective**: Ensure existing flows still work without NotebookDB.

#### Steps:

1. **Disable NotebookDB** (temporary test)
   ```python
   # backend/api/routes.py
   routes.notebook_db = None
   ```

2. **Run Sync**
   - Should fall back to API-based discovery
   - All owned notebooks sync (no selection)

3. **Verify Logs**
   ```
   WARNING - NotebookDB or user_id not available, falling back to API-based notebook discovery
   ```

4. **Re-enable NotebookDB**
   ```python
   routes.notebook_db = notebook_db
   ```

---

## 🐛 Troubleshooting

### Issue: "No notebooks discovered"

**Possible Causes**:
- Missing API permissions
- Token expired
- Network issues

**Solutions**:
1. Check OAuth scopes in settings
2. Verify `Files.Read.All` and `Sites.Read.All` are granted
3. Re-login to refresh token
4. Check backend logs for API errors

---

### Issue: "Failed to access shared notebook"

**Possible Causes**:
- Missing `Sites.Read.All` permission
- Notebook not properly shared
- Invalid site_id extraction

**Solutions**:
1. Verify user has access in OneNote web
2. Check site_id in database: `SELECT site_id FROM notebooks WHERE is_shared=1`
3. Test getNotebookFromWebUrl manually:
   ```bash
   curl -X POST https://graph.microsoft.com/v1.0/me/onenote/notebooks/getNotebookFromWebUrl \
        -H "Authorization: Bearer TOKEN" \
        -d '{"webUrl": "ONENOTE_URL"}'
   ```

---

### Issue: "Sync selects all notebooks instead of selected ones"

**Possible Causes**:
- NotebookDB not initialized
- User ID mismatch
- Selection not saved

**Solutions**:
1. Check logs for "NotebookDB initialized"
2. Verify selection was saved: `SELECT * FROM notebooks WHERE user_id='xxx'`
3. Ensure `is_selected=1` for desired notebooks

---

## 📊 Database Inspection

### Check Discovered Notebooks
```sql
sqlite3 data/notebooks.db

SELECT id, display_name, is_shared, user_role, is_selected, sync_status
FROM notebooks
WHERE user_id = 'your-user-id';
```

### Check Sync Status
```sql
SELECT display_name, sync_status, last_synced_at, page_count, section_count
FROM notebooks
WHERE user_id = 'your-user-id'
ORDER BY last_synced_at DESC;
```

### Reset Selection (for testing)
```sql
UPDATE notebooks SET is_selected = 1 WHERE user_id = 'your-user-id';
```

---

## 🚀 API Testing with cURL

### Discover Notebooks
```bash
curl -H "Authorization: Bearer YOUR_ID_TOKEN" \
     http://localhost:8000/api/notebooks/discover
```

### Update Selection
```bash
curl -X POST \
     -H "Authorization: Bearer YOUR_ID_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"notebook_ids": ["notebook-1", "notebook-2"]}' \
     http://localhost:8000/api/notebooks/select
```

### Get Status
```bash
curl -H "Authorization: Bearer YOUR_ID_TOKEN" \
     http://localhost:8000/api/notebooks/status
```

### Trigger Sync
```bash
curl -X POST \
     -H "Authorization: Bearer YOUR_ID_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"full_sync": false}' \
     http://localhost:8000/api/index/sync
```

---

## ✅ Success Criteria

The implementation is successful if:

1. ✅ Notebooks from all 3 sources are discovered
2. ✅ Shared notebooks appear with "Shared by [owner]" badge
3. ✅ User can select/deselect notebooks
4. ✅ Selection persists across sessions
5. ✅ Sync respects notebook selection
6. ✅ Shared notebooks sync without 403 errors
7. ✅ Site-scoped endpoints are used (check logs)
8. ✅ Notebook sync status is tracked per notebook
9. ✅ Query responses include content from selected notebooks
10. ✅ Backward compatibility maintained (works without NotebookDB)

---

## 📝 Next Steps

### Future Enhancements

1. **Notebook Groups**
   - Group notebooks by: Owned, Shared, Recent
   - Save group selections

2. **Selective Section Sync**
   - Allow selecting specific sections within notebooks
   - Finer-grained control

3. **Sync Scheduling**
   - Per-notebook sync schedules
   - Priority sync for frequently accessed notebooks

4. **Team Notebooks**
   - Discover notebooks from Microsoft Teams
   - `/groups/{group-id}/onenote/notebooks` endpoint

5. **Advanced Permissions**
   - Show read-only indicator for Reader role
   - Disable sync for restricted notebooks

---

## 🎉 Conclusion

The notebook selection and shared notebook support has been fully implemented and integrated into your OneNote RAG system. The solution uses the innovative `getNotebookFromWebUrl` approach to unify access to both owned and shared notebooks through site-scoped API endpoints.

**Key Achievements**:
- ✅ Unified API access for owned + shared notebooks
- ✅ User-friendly notebook selection UI
- ✅ Persistent user preferences
- ✅ Real-time sync status tracking
- ✅ Backward compatible design

Follow the testing guide above to verify all functionality works as expected!
