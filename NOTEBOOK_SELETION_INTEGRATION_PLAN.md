# OneNote Notebook Selection Integration Plan
 
**Date:** November 24, 2025  
**Goal:** Enable users to discover, select, and work with both owned and shared OneNote notebooks in the RAG system
 
---
 
## Table of Contents
 
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Backend Changes](#backend-changes)
4. [Frontend Changes](#frontend-changes)
5. [Database Schema Updates](#database-schema-updates)
6. [API Endpoints](#api-endpoints)
7. [User Flow](#user-flow)
8. [Implementation Phases](#implementation-phases)
9. [Testing Strategy](#testing-strategy)
10. [Migration Plan](#migration-plan)
 
---
 
## 1. Overview
 
### Current State
- ✅ Users authenticate via Microsoft SSO
- ✅ System syncs from `/me/onenote/notebooks` (owned notebooks only)
- ✅ Automatic sync with document cache
- ❌ Shared notebooks not accessible
- ❌ No notebook selection UI
 
### Target State
- ✅ Discover notebooks from 3 sources (owned, recent, shared)
- ✅ UI to select which notebooks to sync
- ✅ Support both owned and shared notebooks
- ✅ Seamless integration with existing RAG workflow
- ✅ Per-user notebook preferences
 
### Key Innovation
Use `getNotebookFromWebUrl` to normalize any notebook (owned or shared) into a proper OneNote object with siteId, enabling unified access via site-scoped endpoints.
 
---
 
## 2. Architecture
 
### High-Level Flow
 
```
┌─────────────────────────────────────────────────────────────────┐
│                      USER AUTHENTICATION                         │
│                  (Microsoft SSO - existing)                      │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    NOTEBOOK DISCOVERY                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Owned      │  │   Recent     │  │   Shared     │          │
│  │ /notebooks   │  │ /getRecent   │  │/sharedWithMe │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         └──────────────────┴──────────────────┘                  │
│                           │                                      │
│                  Extract webUrl for each                         │
│                           │                                      │
│                           ▼                                      │
│              ┌─────────────────────────┐                         │
│              │ getNotebookFromWebUrl   │                         │
│              │   (Normalization)       │                         │
│              └──────────┬──────────────┘                         │
│                         │                                        │
│           Returns: id, siteId, sectionsUrl,                      │
│                    userRole, isShared                            │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FRONTEND UI DISPLAY                           │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Notebook Selection UI                                  │    │
│  │  ┌───────────────────────┐  ┌───────────────────────┐  │    │
│  │  │ My Notebooks          │  │ Shared with Me        │  │    │
│  │  │ ✓ Personal Notes      │  │ □ desk-notes (Rukai)  │  │    │
│  │  │ □ Work Notebook       │  │ □ Team Research       │  │    │
│  │  └───────────────────────┘  └───────────────────────┘  │    │
│  │                    [Sync Selected Notebooks]            │    │
│  └─────────────────────────────────────────────────────────┘    │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                  BACKEND SYNC ORCHESTRATOR                       │
│  For each selected notebook:                                    │
│    1. Use siteId for site-scoped access                         │
│    2. GET /sites/{siteId}/onenote/notebooks/{id}/sections       │
│    3. For each section: GET .../sections/{id}/pages             │
│    4. For each page: GET .../pages/{id}/content?includeIDs=true │
│    5. Parse HTML, extract text, chunk                           │
│    6. Generate embeddings                                       │
│    7. Store in vector DB with notebook metadata                 │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                 EXISTING RAG QUERY WORKFLOW                      │
│  User asks question → Retrieve relevant chunks → LLM response   │
│  (No changes needed - works with existing infrastructure)       │
└─────────────────────────────────────────────────────────────────┘
```
 
---
 
## 3. Backend Changes
 
### 3.1 New Services
 
#### **`services/onenote_discovery_service.py`**
 
```python
class OneNoteDiscoveryService:
    """Discover and normalize OneNote notebooks from multiple sources."""
   
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.graph_base_url = "https://graph.microsoft.com/v1.0"
   
    async def discover_all_notebooks(self) -> List[NotebookCandidate]:
        """
        Discover notebooks from 3 sources:
        1. Owned: /me/onenote/notebooks
        2. Recent: /me/onenote/notebooks/getRecentNotebooks
        3. Shared: /me/drive/sharedWithMe (filter package.type="oneNote")
       
        Returns: List of candidates with webUrl
        """
        pass
   
    async def normalize_notebook(self, web_url: str) -> NormalizedNotebook:
        """
        Normalize notebook via getNotebookFromWebUrl.
       
        POST /me/onenote/notebooks/getNotebookFromWebUrl
        Body: {"webUrl": web_url}
       
        Returns: {id, siteId, displayName, sectionsUrl, userRole, isShared}
        """
        pass
   
    def extract_site_id(self, self_url: str) -> str:
        """Extract siteId from self URL using regex."""
        pass
```
 
#### **`services/onenote_sync_service.py`** (Update existing)
 
```python
class OneNoteSyncService:
    """Updated to handle both owned and shared notebooks."""
   
    async def sync_notebook(
        self,
        notebook_id: str,
        site_id: str,  # NEW: Required for shared notebooks
        user_id: str
    ):
        """
        Sync notebook using site-scoped endpoints.
       
        Uses: /sites/{siteId}/onenote/notebooks/{notebookId}/...
        instead of: /me/onenote/notebooks/{notebookId}/...
        """
        pass
   
    async def get_sections(self, notebook_id: str, site_id: str):
        """GET /sites/{siteId}/onenote/notebooks/{notebookId}/sections"""
        pass
   
    async def get_pages(self, section_id: str, site_id: str):
        """GET /sites/{siteId}/onenote/sections/{sectionId}/pages"""
        pass
   
    async def get_page_content(self, page_id: str, site_id: str):
        """GET /sites/{siteId}/onenote/pages/{pageId}/content?includeIDs=true"""
        pass
```
 
### 3.2 Updated Models
 
#### **`models/notebook.py`**
 
```python
class Notebook(Base):
    """Enhanced to support shared notebooks."""
    __tablename__ = "notebooks"
   
    id = Column(String, primary_key=True)  # OneNote ID
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
   
    # Existing fields
    display_name = Column(String, nullable=False)
    created_datetime = Column(DateTime)
    last_modified_datetime = Column(DateTime)
   
    # NEW: Required for shared notebooks
    site_id = Column(String, nullable=False)  # SharePoint site ID
    is_shared = Column(Boolean, default=False)
    user_role = Column(String)  # "Owner", "Contributor", "Reader"
    shared_by = Column(String, nullable=True)  # Display name of owner
   
    # NEW: Discovery metadata
    web_url = Column(String)
    sections_url = Column(String)
   
    # NEW: User preference
    is_selected = Column(Boolean, default=True)  # User wants to sync this
   
    # Existing relationships
    sections = relationship("Section", back_populates="notebook")
```
 
### 3.3 Data Migration
 
#### **`migrations/add_notebook_site_id.py`**
 
```python
"""
Migration: Add site_id and shared notebook fields
"""
 
def upgrade():
    # Add new columns
    op.add_column('notebooks', sa.Column('site_id', sa.String(), nullable=True))
    op.add_column('notebooks', sa.Column('is_shared', sa.Boolean(), default=False))
    op.add_column('notebooks', sa.Column('user_role', sa.String(), nullable=True))
    op.add_column('notebooks', sa.Column('shared_by', sa.String(), nullable=True))
    op.add_column('notebooks', sa.Column('web_url', sa.String(), nullable=True))
    op.add_column('notebooks', sa.Column('sections_url', sa.String(), nullable=True))
    op.add_column('notebooks', sa.Column('is_selected', sa.Boolean(), default=True))
   
    # For existing notebooks, populate site_id by calling getNotebookFromWebUrl
    # (This will be done via a one-time admin script)
```
 
---
 
## 4. Frontend Changes
 
### 4.1 New Components
 
#### **`frontend/src/components/NotebookSelector/NotebookSelector.tsx`**
 
```tsx
interface NotebookSelectorProps {
  onClose: () => void;
  onNotebooksSelected: (notebookIds: string[]) => Promise<void>;
}
 
export function NotebookSelector({ onClose, onNotebooksSelected }: NotebookSelectorProps) {
  const [notebooks, setNotebooks] = useState<NotebookInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
 
  useEffect(() => {
    // Fetch discovered notebooks on mount
    fetchDiscoveredNotebooks();
  }, []);
 
  const fetchDiscoveredNotebooks = async () => {
    const response = await fetch('/api/notebooks/discover');
    const data = await response.json();
    setNotebooks(data.notebooks);
   
    // Pre-select currently synced notebooks
    const currentlySelected = data.notebooks
      .filter(nb => nb.isSelected)
      .map(nb => nb.id);
    setSelectedIds(new Set(currentlySelected));
  };
 
  const handleSyncSelected = async () => {
    setLoading(true);
    await onNotebooksSelected(Array.from(selectedIds));
    setLoading(false);
    onClose();
  };
 
  return (
    <Dialog open onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>Select Notebooks to Sync</DialogTitle>
      <DialogContent>
        <Tabs>
          <Tab label="My Notebooks" />
          <Tab label="Shared with Me" />
        </Tabs>
       
        <NotebookList
          notebooks={notebooks}
          selectedIds={selectedIds}
          onToggle={(id) => toggleNotebook(id)}
        />
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button
          onClick={handleSyncSelected}
          variant="contained"
          disabled={loading || selectedIds.size === 0}
        >
          Sync {selectedIds.size} Notebook(s)
        </Button>
      </DialogActions>
    </Dialog>
  );
}
```
 
#### **`frontend/src/components/NotebookSelector/NotebookCard.tsx`**
 
```tsx
interface NotebookCardProps {
  notebook: NotebookInfo;
  isSelected: boolean;
  onToggle: () => void;
}
 
export function NotebookCard({ notebook, isSelected, onToggle }: NotebookCardProps) {
  return (
    <Card variant="outlined" sx={{ mb: 1 }}>
      <CardContent>
        <Stack direction="row" spacing={2} alignItems="center">
          <Checkbox checked={isSelected} onChange={onToggle} />
         
          <Box flex={1}>
            <Typography variant="h6">
              {notebook.displayName}
            </Typography>
           
            <Stack direction="row" spacing={1} sx={{ mt: 0.5 }}>
              {notebook.isShared && (
                <Chip
                  size="small"
                  label={`Shared by ${notebook.sharedBy}`}
                  icon={<PeopleIcon />}
                />
              )}
              <Chip
                size="small"
                label={notebook.userRole}
                variant="outlined"
              />
            </Stack>
           
            <Typography variant="caption" color="text.secondary">
              Last modified: {formatDate(notebook.lastModifiedDateTime)}
            </Typography>
          </Box>
         
          <Box>
            <IconButton href={notebook.webUrl} target="_blank">
              <OpenInNewIcon />
            </IconButton>
          </Box>
        </Stack>
      </CardContent>
    </Card>
  );
}
```
 
### 4.2 Integration Points
 
#### **Update `frontend/src/components/Settings/Settings.tsx`**
 
```tsx
export function Settings() {
  const [showNotebookSelector, setShowNotebookSelector] = useState(false);
 
  return (
    <Box>
      {/* Existing settings... */}
     
      <Divider sx={{ my: 2 }} />
     
      <Typography variant="h6" gutterBottom>
        OneNote Notebooks
      </Typography>
     
      <Button
        variant="outlined"
        startIcon={<NotebookIcon />}
        onClick={() => setShowNotebookSelector(true)}
      >
        Manage Notebooks
      </Button>
     
      {showNotebookSelector && (
        <NotebookSelector
          onClose={() => setShowNotebookSelector(false)}
          onNotebooksSelected={handleNotebooksSelected}
        />
      )}
    </Box>
  );
}
```
 
#### **Add to `frontend/src/components/Chat/ChatInterface.tsx`**
 
```tsx
// Show current notebook context in chat
<Box sx={{ p: 2, bgcolor: 'background.paper' }}>
  <Typography variant="caption" color="text.secondary">
    Searching in: {selectedNotebooks.map(nb => nb.displayName).join(', ')}
  </Typography>
</Box>
```
 
---
 
## 5. Database Schema Updates
 
### Before (Current)
 
```sql
CREATE TABLE notebooks (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    display_name VARCHAR NOT NULL,
    created_datetime TIMESTAMP,
    last_modified_datetime TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```
 
### After (Enhanced)
 
```sql
CREATE TABLE notebooks (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    display_name VARCHAR NOT NULL,
    created_datetime TIMESTAMP,
    last_modified_datetime TIMESTAMP,
   
    -- NEW: Shared notebook support
    site_id VARCHAR NOT NULL,           -- SharePoint site ID
    is_shared BOOLEAN DEFAULT FALSE,    -- Is this a shared notebook?
    user_role VARCHAR,                  -- Owner, Contributor, Reader
    shared_by VARCHAR,                  -- Display name of owner
   
    -- NEW: Discovery metadata
    web_url VARCHAR,                    -- OneNote web URL
    sections_url VARCHAR,               -- API endpoint for sections
   
    -- NEW: User preference
    is_selected BOOLEAN DEFAULT TRUE,   -- User wants to sync this
   
    FOREIGN KEY (user_id) REFERENCES users(id)
);
 
-- Index for filtering selected notebooks
CREATE INDEX idx_notebooks_user_selected
ON notebooks(user_id, is_selected);
 
-- Index for shared notebooks
CREATE INDEX idx_notebooks_shared
ON notebooks(is_shared);
```
 
---
 
## 6. API Endpoints
 
### 6.1 Discovery Endpoints
 
#### **`GET /api/notebooks/discover`**
 
**Purpose:** Discover all accessible notebooks (owned + shared)
 
**Response:**
```json
{
  "notebooks": [
    {
      "id": "1-af85c8b8-...",
      "displayName": "Personal Notes",
      "siteId": "...",
      "isShared": false,
      "userRole": "Owner",
      "webUrl": "https://...",
      "lastModifiedDateTime": "2025-11-24T10:00:00Z",
      "isSelected": true
    },
    {
      "id": "1-c58a1e27-...",
      "displayName": "desk-notes",
      "siteId": "...",
      "isShared": true,
      "userRole": "Owner",
      "sharedBy": "Rukai Lou",
      "webUrl": "https://...",
      "lastModifiedDateTime": "2025-11-21T02:43:39Z",
      "isSelected": false
    }
  ],
  "total": 5,
  "bySource": {
    "owned": 1,
    "recent": 1,
    "shared": 3
  }
}
```
 
**Implementation:**
```python
@router.get("/notebooks/discover")
async def discover_notebooks(
    current_user: User = Depends(get_current_user)
):
    """Discover all accessible notebooks."""
    discovery_service = OneNoteDiscoveryService(current_user.access_token)
   
    # 1. Discover from 3 sources
    candidates = await discovery_service.discover_all_notebooks()
   
    # 2. Normalize each via getNotebookFromWebUrl
    normalized = []
    for candidate in candidates:
        nb = await discovery_service.normalize_notebook(candidate.web_url)
        normalized.append(nb)
   
    # 3. Check which are already in DB
    existing_ids = {nb.id for nb in db.query(Notebook).filter_by(user_id=current_user.id)}
   
    # 4. Merge with DB state
    for nb in normalized:
        if nb.id in existing_ids:
            nb.is_selected = db.query(Notebook).get(nb.id).is_selected
   
    return {"notebooks": normalized, "total": len(normalized)}
```
 
---
 
#### **`POST /api/notebooks/select`**
 
**Purpose:** Update which notebooks the user wants to sync
 
**Request:**
```json
{
  "notebookIds": ["1-af85c8b8-...", "1-c58a1e27-..."]
}
```
 
**Response:**
```json
{
  "success": true,
  "selected": 2,
  "syncStarted": true
}
```
 
**Implementation:**
```python
@router.post("/notebooks/select")
async def select_notebooks(
    request: NotebookSelectionRequest,
    current_user: User = Depends(get_current_user),
    background_tasks: BackgroundTasks
):
    """Update selected notebooks and trigger sync."""
   
    # 1. Update is_selected in database
    db.query(Notebook).filter_by(user_id=current_user.id).update({
        "is_selected": False
    })
   
    db.query(Notebook).filter(
        Notebook.id.in_(request.notebookIds),
        Notebook.user_id == current_user.id
    ).update({"is_selected": True})
   
    db.commit()
   
    # 2. Trigger background sync for selected notebooks
    background_tasks.add_task(
        sync_selected_notebooks,
        current_user.id,
        request.notebookIds
    )
   
    return {
        "success": True,
        "selected": len(request.notebookIds),
        "syncStarted": True
    }
```
 
---
 
#### **`GET /api/notebooks/status`**
 
**Purpose:** Get sync status for all notebooks
 
**Response:**
```json
{
  "notebooks": [
    {
      "id": "1-af85c8b8-...",
      "displayName": "Personal Notes",
      "isSelected": true,
      "syncStatus": "completed",
      "lastSyncedAt": "2025-11-24T10:30:00Z",
      "pageCount": 42,
      "sectionCount": 5
    }
  ]
}
```
 
---
 
### 6.2 Existing Endpoints (No Changes)
 
These endpoints continue to work as-is:
- `POST /api/chat` - Query with RAG (works with all synced notebooks)
- `GET /api/documents` - List all indexed documents
- `GET /api/sync/status` - Overall sync status
 
---
 
## 7. User Flow
 
### 7.1 First-Time Setup
 
```
1. User logs in via Microsoft SSO
   ↓
2. Redirect to Settings > Notebooks
   ↓
3. Show "Discovering your notebooks..." loading state
   ↓
4. Display NotebookSelector with discovered notebooks
   ↓
5. User selects desired notebooks (pre-select owned notebooks)
   ↓
6. User clicks "Sync Selected Notebooks"
   ↓
7. Backend starts syncing in background
   ↓
8. Show progress: "Syncing 2/5 notebooks..."
   ↓
9. When complete: "✅ Ready! You can now ask questions."
   ↓
10. Redirect to Chat interface
```
 
### 7.2 Ongoing Usage
 
```
User opens app
   ↓
Already synced? → Go to Chat directly
   ↓
User asks question
   ↓
RAG searches across all selected notebooks
   ↓
Results show source notebook for each answer
```
 
### 7.3 Adding More Notebooks
 
```
User goes to Settings > Notebooks
   ↓
Click "Manage Notebooks"
   ↓
Select additional notebooks
   ↓
Click "Sync Selected"
   ↓
Background sync starts (doesn't interrupt current session)
   ↓
Toast notification: "✅ desk-notes synced successfully"
```
 
---
 
## 8. Implementation Phases
 
### Phase 1: Backend Discovery (Week 1)
**Goal:** Implement notebook discovery and normalization
 
**Tasks:**
1. ✅ Create `OneNoteDiscoveryService`
2. ✅ Implement `discover_all_notebooks()` method
3. ✅ Implement `normalize_notebook()` method
4. ✅ Create `GET /api/notebooks/discover` endpoint
5. ✅ Add unit tests
6. ✅ Test with real Microsoft Graph API
 
**Deliverable:** Backend can discover and normalize notebooks
 
---
 
### Phase 2: Database Schema (Week 1)
**Goal:** Update database to support shared notebooks
 
**Tasks:**
1. ✅ Create migration script for new columns
2. ✅ Update `Notebook` model with new fields
3. ✅ Write data migration script for existing notebooks
4. ✅ Test migration on staging database
5. ✅ Add indexes for performance
 
**Deliverable:** Database ready for shared notebook metadata
 
---
 
### Phase 3: Backend Sync Updates (Week 2)
**Goal:** Update sync to use site-scoped endpoints
 
**Tasks:**
1. ✅ Update `OneNoteSyncService.get_sections()` to use site_id
2. ✅ Update `OneNoteSyncService.get_pages()` to use site_id
3. ✅ Update `OneNoteSyncService.get_page_content()` to use site_id
4. ✅ Add fallback logic (try site-scoped, fall back to direct)
5. ✅ Update sync orchestrator to pass site_id
6. ✅ Add comprehensive logging
7. ✅ Test with both owned and shared notebooks
 
**Deliverable:** Sync works for both owned and shared notebooks
 
---
 
### Phase 4: Selection API (Week 2)
**Goal:** Allow users to select notebooks
 
**Tasks:**
1. ✅ Create `POST /api/notebooks/select` endpoint
2. ✅ Implement notebook selection persistence
3. ✅ Add background task for triggering sync
4. ✅ Create `GET /api/notebooks/status` endpoint
5. ✅ Add WebSocket for real-time sync progress
6. ✅ Test API endpoints
 
**Deliverable:** Backend API for notebook selection
 
---
 
### Phase 5: Frontend UI (Week 3)
**Goal:** Build notebook selection interface
 
**Tasks:**
1. ✅ Create `NotebookSelector` component
2. ✅ Create `NotebookCard` component
3. ✅ Create `NotebookList` component
4. ✅ Add to Settings page
5. ✅ Implement selection state management
6. ✅ Add loading states and error handling
7. ✅ Style components (Material-UI)
 
**Deliverable:** Working notebook selection UI
 
---
 
### Phase 6: Integration & UX Polish (Week 3-4)
**Goal:** Integrate everything and polish UX
 
**Tasks:**
1. ✅ Add notebook context to chat interface
2. ✅ Show source notebook in search results
3. ✅ Add first-time setup wizard
4. ✅ Implement sync progress indicators
5. ✅ Add toast notifications
6. ✅ Write user documentation
7. ✅ Add tooltips and help text
 
**Deliverable:** Polished, production-ready feature
 
---
 
### Phase 7: Testing & Deployment (Week 4)
**Goal:** Comprehensive testing and deployment
 
**Tasks:**
1. ✅ End-to-end testing (owned notebooks)
2. ✅ End-to-end testing (shared notebooks)
3. ✅ Performance testing (large notebooks)
4. ✅ Error handling testing (network failures, auth expiry)
5. ✅ User acceptance testing
6. ✅ Deploy to staging
7. ✅ Deploy to production
 
**Deliverable:** Feature live in production
 
---
 
## 9. Testing Strategy
 
### 9.1 Unit Tests
 
**Backend:**
```python
# test_discovery_service.py
def test_discover_owned_notebooks():
    """Test discovering owned notebooks."""
    pass
 
def test_discover_shared_notebooks():
    """Test discovering shared notebooks from sharedWithMe."""
    pass
 
def test_normalize_notebook():
    """Test getNotebookFromWebUrl normalization."""
    pass
 
def test_extract_site_id():
    """Test siteId extraction from self URL."""
    pass
 
# test_sync_service.py
def test_sync_owned_notebook():
    """Test syncing owned notebook with direct endpoints."""
    pass
 
def test_sync_shared_notebook():
    """Test syncing shared notebook with site-scoped endpoints."""
    pass
 
def test_site_scoped_sections():
    """Test retrieving sections via site-scoped endpoint."""
    pass
```
 
**Frontend:**
```tsx
// NotebookSelector.test.tsx
describe('NotebookSelector', () => {
  it('fetches and displays notebooks', async () => {});
  it('allows selecting multiple notebooks', () => {});
  it('shows loading state during sync', () => {});
  it('displays error on API failure', () => {});
});
 
// NotebookCard.test.tsx
describe('NotebookCard', () => {
  it('displays notebook metadata', () => {});
  it('shows shared badge for shared notebooks', () => {});
  it('handles toggle selection', () => {});
});
```
 
---
 
### 9.2 Integration Tests
 
```python
# test_notebook_flow.py
async def test_complete_notebook_workflow():
    """
    Test complete flow:
    1. Discover notebooks
    2. Select notebooks
    3. Sync notebooks
    4. Query with RAG
    5. Verify results include source notebooks
    """
    # 1. Discover
    response = await client.get("/api/notebooks/discover")
    assert response.status_code == 200
    notebooks = response.json()["notebooks"]
    assert len(notebooks) > 0
   
    # 2. Select
    selected_ids = [nb["id"] for nb in notebooks[:2]]
    response = await client.post("/api/notebooks/select", json={
        "notebookIds": selected_ids
    })
    assert response.json()["success"] == True
   
    # 3. Wait for sync
    await wait_for_sync_completion()
   
    # 4. Query
    response = await client.post("/api/chat", json={
        "query": "test query"
    })
   
    # 5. Verify
    assert "source_notebook" in response.json()["sources"][0]
```
 
---
 
### 9.3 E2E Tests (Playwright)
 
```typescript
// e2e/notebook-selection.spec.ts
test('user can select and sync notebooks', async ({ page }) => {
  // Login
  await page.goto('/login');
  await loginWithMicrosoft(page);
 
  // Go to settings
  await page.click('[data-testid="settings-button"]');
  await page.click('[data-testid="manage-notebooks"]');
 
  // Select notebooks
  await page.check('[data-testid="notebook-1-af85c8b8"]');
  await page.check('[data-testid="notebook-1-c58a1e27"]');
 
  // Sync
  await page.click('[data-testid="sync-selected"]');
 
  // Wait for completion
  await page.waitForSelector('[data-testid="sync-complete"]');
 
  // Go to chat
  await page.goto('/chat');
 
  // Verify notebook context shown
  await expect(page.locator('[data-testid="notebook-context"]')).toContainText('Personal Notes, desk-notes');
});
```
 
---
 
## 10. Migration Plan
 
### 10.1 Existing Users
 
**Challenge:** Existing users have notebooks synced via old method (without site_id)
 
**Solution:**
 
1. **Migration Script:**
```python
# scripts/backfill_site_ids.py
async def backfill_site_ids():
    """Backfill site_id for existing notebooks."""
   
    notebooks = db.query(Notebook).filter(Notebook.site_id == None).all()
   
    for notebook in notebooks:
        try:
            # Get user's access token
            user = notebook.user
           
            # Fetch notebook via Graph API to get webUrl
            response = requests.get(
                f"{GRAPH_URL}/me/onenote/notebooks/{notebook.id}",
                headers={"Authorization": f"Bearer {user.access_token}"}
            )
            web_url = response.json()["links"]["oneNoteWebUrl"]["href"]
           
            # Normalize to get siteId
            discovery = OneNoteDiscoveryService(user.access_token)
            normalized = await discovery.normalize_notebook(web_url)
           
            # Update database
            notebook.site_id = normalized.site_id
            notebook.web_url = web_url
            notebook.is_shared = False  # Old notebooks were owned
            notebook.user_role = "Owner"
           
            db.commit()
           
            print(f"✅ Updated {notebook.display_name}")
           
        except Exception as e:
            print(f"❌ Failed {notebook.display_name}: {e}")
```
 
2. **Gradual Rollout:**
   - Week 1: Deploy migration script, run on staging
   - Week 2: Run on 10% of production users
   - Week 3: Run on 50% of production users
   - Week 4: Complete migration for all users
 
---
 
### 10.2 Rollback Plan
 
**If issues arise:**
 
1. **Database Rollback:**
```sql
-- Remove new columns (data preserved)
ALTER TABLE notebooks DROP COLUMN site_id;
ALTER TABLE notebooks DROP COLUMN is_shared;
-- ... etc
```
 
2. **Code Rollback:**
   - Revert to previous deployment
   - Old code ignores new columns (doesn't break)
 
3. **Graceful Degradation:**
   - If site_id missing, fall back to direct endpoints
   - Log warning, continue working for owned notebooks
 
---
 
## 11. Edge Cases & Error Handling
 
### 11.1 Network Errors
 
**Scenario:** Graph API call fails during discovery
 
**Solution:**
- Retry with exponential backoff (3 attempts)
- Show user-friendly error: "Could not connect to Microsoft. Please try again."
- Cache previous discovery results, show stale data with warning
 
---
 
### 11.2 Access Token Expiry
 
**Scenario:** Token expires during sync
 
**Solution:**
- Catch 401 Unauthorized
- Trigger token refresh flow
- Retry operation with new token
- If refresh fails, prompt user to re-authenticate
 
---
 
### 11.3 Notebook Access Revoked
 
**Scenario:** User loses access to shared notebook
 
**Solution:**
- Catch 403 Forbidden during sync
- Mark notebook as `access_revoked = True`
- Remove from selected notebooks
- Show notification: "You no longer have access to 'desk-notes'"
- Don't delete existing indexed content (user may want to keep)
 
---
 
### 11.4 Large Notebook Sync
 
**Scenario:** Notebook with 1000+ pages
 
**Solution:**
- Implement pagination (100 pages per batch)
- Show progress: "Syncing desk-notes: 234/1000 pages"
- Allow cancellation
- Use queue system for background processing
- Rate limiting: Max 10 requests/second to Graph API
 
---
 
### 11.5 Duplicate Notebooks
 
**Scenario:** Same notebook appears in "owned" and "shared"
 
**Solution:**
- Deduplicate by OneNote ID
- Prefer "owned" source over "shared"
- Show single entry with "You own this" badge
 
---
 
## 12. Performance Considerations
 
### 12.1 Discovery Caching
 
**Problem:** Discovery hits 3 API endpoints, slow
 
**Solution:**
```python
# Cache discovery results for 5 minutes
@cache(expire=300)
async def discover_all_notebooks(user_id: str):
    # ... discovery logic
    pass
```
 
---
 
### 12.2 Incremental Sync
 
**Problem:** Re-syncing entire notebook on every change
 
**Solution:**
```python
async def incremental_sync(notebook_id: str, last_sync: datetime):
    """Only sync pages modified since last_sync."""
   
    pages = await get_pages(section_id)
   
    new_or_updated = [
        p for p in pages
        if parse_datetime(p["lastModifiedDateTime"]) > last_sync
    ]
   
    # Only process these pages
    for page in new_or_updated:
        await sync_page(page)
```
 
---
 
### 12.3 Parallel Processing
 
**Problem:** Syncing 5 notebooks serially takes too long
 
**Solution:**
```python
import asyncio
 
async def sync_all_selected(user_id: str):
    """Sync notebooks in parallel."""
   
    notebooks = get_selected_notebooks(user_id)
   
    # Sync up to 3 notebooks concurrently
    semaphore = asyncio.Semaphore(3)
   
    async def sync_with_limit(notebook):
        async with semaphore:
            await sync_notebook(notebook)
   
    await asyncio.gather(*[
        sync_with_limit(nb) for nb in notebooks
    ])
```
 
---
 
## 13. Security Considerations
 
### 13.1 Authorization
 
**Requirement:** Users can only access their own notebooks
 
**Implementation:**
```python
@router.get("/notebooks/discover")
async def discover_notebooks(
    current_user: User = Depends(get_current_user)
):
    # Use current_user.access_token (user's own token)
    # Can only discover notebooks accessible to this user
    pass
```
 
---
 
### 13.2 Shared Notebook Permissions
 
**Requirement:** Respect SharePoint permissions
 
**Implementation:**
- Use site-scoped endpoints (enforces SharePoint ACLs)
- Store `user_role` (Owner/Contributor/Reader)
- For Reader role: Don't attempt to modify content
- Periodic permission check: Re-discover to detect revoked access
 
---
 
### 13.3 Data Isolation
 
**Requirement:** User A can't see User B's notebooks
 
**Implementation:**
```python
# Always filter by user_id
notebooks = db.query(Notebook).filter_by(user_id=current_user.id).all()
 
# Vector DB: Add user_id to metadata
metadata = {
    "user_id": current_user.id,
    "notebook_id": notebook.id,
    # ...
}
 
# Query: Filter by user_id
results = vector_db.query(
    query_embedding,
    filter={"user_id": current_user.id}
)
```
 
---
 
## 14. Monitoring & Observability
 
### 14.1 Metrics to Track
 
```python
# Prometheus metrics
notebooks_discovered = Counter('notebooks_discovered_total', 'Total notebooks discovered')
notebooks_synced = Counter('notebooks_synced_total', 'Total notebooks synced')
sync_duration = Histogram('sync_duration_seconds', 'Time to sync notebook')
discovery_errors = Counter('discovery_errors_total', 'Discovery failures')
```
 
### 14.2 Logging
 
```python
logger.info(
    "Notebook sync started",
    extra={
        "user_id": user.id,
        "notebook_id": notebook.id,
        "notebook_name": notebook.display_name,
        "is_shared": notebook.is_shared,
        "site_id": notebook.site_id
    }
)
```
 
### 14.3 Alerts
 
- **Alert:** Discovery failing for >10% of requests
- **Alert:** Sync queue depth >100 notebooks
- **Alert:** Average sync duration >10 minutes
 
---
 
## 15. Documentation
 
### 15.1 User Documentation
 
**"How to Add Shared Notebooks"**
1. Click Settings → Manage Notebooks
2. You'll see all notebooks you have access to
3. Check the notebooks you want to search
4. Click "Sync Selected Notebooks"
5. Wait for sync to complete (progress shown)
6. Start asking questions!
 
### 15.2 Developer Documentation
 
**"Adding a New Discovery Source"**
```python
# In OneNoteDiscoveryService
async def discover_from_teams(self):
    """Discover notebooks from Microsoft Teams."""
    # Implementation...
    pass
 
# Register in discover_all_notebooks()
all_candidates.extend(await self.discover_from_teams())
```
 
---
 
## 16. Success Metrics
 
### 16.1 Technical Metrics
- ✅ Discovery latency <3 seconds
- ✅ Sync success rate >95%
- ✅ API error rate <1%
- ✅ P95 sync duration <5 minutes for typical notebook
 
### 16.2 User Metrics
- ✅ % users with shared notebooks selected
- ✅ Average notebooks per user
- ✅ User satisfaction score (survey)
 
---
 
## 17. Future Enhancements
 
### 17.1 Automatic Discovery
- Background job to discover new shared notebooks weekly
- Notify user: "You have access to 2 new notebooks. Add them?"
 
### 17.2 Notebook Groups
- Allow users to create groups: "Work", "Personal", "Research"
- Query specific group: "Search only in Work notebooks"
 
### 17.3 Selective Section Sync
- Let user choose specific sections within notebook
- Example: Sync only "Meeting Notes" section from desk-notes
 
### 17.4 Real-time Sync
- Use Microsoft Graph webhooks for change notifications
- Sync immediately when page modified in OneNote
 
---
 
## Appendix: Complete File Structure
 
```
backend/
├── api/
│   └── notebooks.py              # NEW: Discovery & selection endpoints
├── services/
│   ├── onenote_discovery_service.py  # NEW: Discovery & normalization
│   └── onenote_sync_service.py       # UPDATED: Site-scoped endpoints
├── models/
│   └── notebook.py               # UPDATED: Add site_id, is_shared, etc.
├── migrations/
│   └── add_notebook_site_id.py   # NEW: Schema migration
└── scripts/
    └── backfill_site_ids.py      # NEW: Migration script
 
frontend/
├── src/
│   ├── components/
│   │   ├── NotebookSelector/
│   │   │   ├── NotebookSelector.tsx      # NEW: Main selector dialog
│   │   │   ├── NotebookCard.tsx          # NEW: Individual notebook card
│   │   │   ├── NotebookList.tsx          # NEW: List container
│   │   │   └── index.ts
│   │   ├── Settings/
│   │   │   └── Settings.tsx              # UPDATED: Add notebook management
│   │   └── Chat/
│   │       └── ChatInterface.tsx         # UPDATED: Show notebook context
│   ├── services/
│   │   └── notebookService.ts    # NEW: API client for notebooks
│   └── types/
│       └── notebook.ts           # NEW: TypeScript types
 
tests/
├── backend/
│   ├── test_discovery_service.py
│   ├── test_sync_service.py
│   └── test_notebook_flow.py
└── e2e/
    └── notebook-selection.spec.ts
```
 
---
 
## Summary
 
This comprehensive plan provides a complete roadmap for integrating shared notebook selection into the OneNote RAG system. The key innovation is using `getNotebookFromWebUrl` to normalize any notebook (owned or shared) and extract the crucial `siteId` for site-scoped API access, eliminating sync delays and enabling seamless multi-notebook support.
 
The implementation is broken into 7 phases over 4 weeks, with clear deliverables, testing strategy, and contingency plans for edge cases. The solution maintains backward compatibility with existing notebooks while adding powerful new capabilities for accessing shared content.
 
 