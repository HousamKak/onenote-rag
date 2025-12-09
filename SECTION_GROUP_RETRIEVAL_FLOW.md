# Section Groups Retrieval Flow
 
## Question: How Does Retrieval Work with Section Groups?
 
**Short Answer:**
1. Get all sections first (recursive, includes groups)
2. Then get pages for each section
3. Then get content & images for each page
 
---
 
## Detailed Step-by-Step Flow
 
### 🔄 Complete Sync Flow
 
```
User clicks "Sync" in UI
  ↓
Backend: Get notebooks to sync
  ↓
For each notebook:
  ├─→ Get ALL sections (RECURSIVE) ⭐ This is the key change!
  │   ├─→ Fetch top-level sections
  │   ├─→ Fetch section groups
  │   └─→ For each group, recursively fetch sections (and nested groups)
  │
  ├─→ For each section (now 133 instead of 27):
  │   ├─→ Get all pages in section
  │   └─→ For each page:
  │       ├─→ Get page content (HTML)
  │       ├─→ Extract images from HTML
  │       ├─→ Download images
  │       ├─→ Extract plain text
  │       ├─→ Cache document & images
  │       └─→ Generate embeddings & index
  │
  └─→ Update sync status
```
 
---
 
## Step 1: Get ALL Sections (Recursive)
 
### For Shared Notebooks (desk-notes):
 
```python
# Called from sync_orchestrator.py line 147
sections = await self._fetch_with_rate_limit(
    self.onenote.list_all_sections_recursive_site_scoped,
    site_id,
    notebook_id
)
```
 
### What This Method Does:
 
#### 1a. Fetch Top-Level Sections
```python
# onenote_service.py line 663
top_level = self.list_sections_site_scoped(site_id, notebook_id)
```
 
**API Call:**
```
GET /sites/{siteId}/onenote/notebooks/{notebookId}/sections
```
 
**Returns 27 sections:**
```json
[
  {"id": "sec1", "displayName": "ALPHASENSE"},
  {"id": "sec2", "displayName": "AVDL"},
  {"id": "sec3", "displayName": "BHF"},
  ...
]
```
 
#### 1b. Fetch Section Groups
```python
# onenote_service.py line 668
section_groups = self.list_section_groups_site_scoped(site_id, notebook_id)
```
 
**API Call:**
```
GET /sites/{siteId}/onenote/notebooks/{notebookId}/sectionGroups
```
 
**Returns 25 groups:**
```json
[
  {"id": "grp1", "displayName": "AES"},
  {"id": "grp2", "displayName": "AKRO NOVO"},
  {"id": "grp3", "displayName": "AL"},
  ...
]
```
 
#### 1c. For Each Group, Get Sections Recursively
```python
# onenote_service.py line 671-673
for group in section_groups:
    group_sections = self._get_sections_from_group_recursive_site_scoped(
        site_id, group['id'], group.get('displayName', 'Unknown')
    )
    all_sections.extend(group_sections)
```
 
**For group "AES":**
 
**API Call:**
```
GET /sites/{siteId}/onenote/sectionGroups/{groupId}/sections
```
 
**Returns 4 sections:**
```json
[
  {"id": "sec_aes1", "displayName": "Expert Calls"},
  {"id": "sec_aes2", "displayName": "General Notes"},
  {"id": "sec_aes3", "displayName": "Lawyers"},
  {"id": "sec_aes4", "displayName": "Sell Side"}
]
```
 
**Check for nested groups:**
```
GET /sites/{siteId}/onenote/sectionGroups/{groupId}/sectionGroups
```
 
If nested groups exist, recurse into them (OneNote supports unlimited nesting).
 
#### 1d. Return Flattened List
 
**Final result: 133 sections in a flat array**
```json
[
  {"id": "sec1", "displayName": "ALPHASENSE"},              // Top-level
  {"id": "sec2", "displayName": "AVDL"},                    // Top-level
  ... // 25 more top-level
  {"id": "sec_aes1", "displayName": "Expert Calls"},        // From AES group
  {"id": "sec_aes2", "displayName": "General Notes"},       // From AES group
  {"id": "sec_aes3", "displayName": "Lawyers"},             // From AES group
  {"id": "sec_aes4", "displayName": "Sell Side"},           // From AES group
  {"id": "sec_akro1", "displayName": "Expert Calls"},       // From AKRO NOVO group
  ... // 102 more from all groups
]
```
 
**Key Point:** The hierarchy is flattened! Section groups are only used for discovery, not stored in the result.
 
---
 
## Step 2: Get Pages for Each Section
 
Now we have 133 sections in a flat list. For each section:
 
```python
# sync_orchestrator.py line 167-172
pages = await self._fetch_with_rate_limit(
    self.onenote.list_pages_site_scoped,
    site_id,
    section_id
)
```
 
**API Call (same for ALL sections):**
```
GET /sites/{siteId}/onenote/sections/{sectionId}/pages
```
 
**Works for:**
- ✅ Top-level section (ALPHASENSE)
- ✅ Section in group (Expert Calls from AES)
- ✅ Section in nested group (if any)
 
**Example for "Expert Calls" section in AES group:**
```json
{
  "value": [
    {
      "id": "page1",
      "title": "AES Q3 2024 Call",
      "createdDateTime": "2024-09-15T10:30:00Z",
      "lastModifiedDateTime": "2024-09-16T14:20:00Z",
      "contentUrl": "..."
    },
    {
      "id": "page2",
      "title": "AES Expert Interview - Supply Chain",
      "createdDateTime": "2024-08-10T09:15:00Z",
      "lastModifiedDateTime": "2024-08-10T11:45:00Z",
      "contentUrl": "..."
    }
  ]
}
```
 
---
 
## Step 3: Get Content for Each Page
 
For each page from each section:
 
```python
# sync_orchestrator.py line 662-669
if site_id:
    html_content = await self._fetch_with_rate_limit(
        self.onenote.get_page_content_site_scoped,
        site_id,
        page_id
    )
```
 
**API Call:**
```
GET /sites/{siteId}/onenote/pages/{pageId}/content
```
 
**Returns HTML:**
```html
<html>
  <head>
    <title>AES Q3 2024 Call</title>
  </head>
  <body>
    <h1>AES Q3 2024 Earnings Call</h1>
    <p>Key takeaways from the call...</p>
    <img src="https://graph.microsoft.com/v1.0/siteCollections/.../resources/abc123/$value" />
    <table>...</table>
  </body>
</html>
```
 
---
 
## Step 4: Extract & Download Images
 
### 4a. Extract Image URLs from HTML
```python
# sync_orchestrator.py line 689
images = self._extract_images_from_html(html_content, page_id)
```
 
**Result:**
```python
[
  {
    'src': 'https://graph.microsoft.com/v1.0/siteCollections/.../resources/abc123/$value',
    'alt_text': 'Q3 Performance Chart',
    'resource_id': 'abc123'
  }
]
```
 
### 4b. Fix Image URLs
```python
# sync_orchestrator.py line 920-923
if 'siteCollections' in image_url:
    logger.debug(f"Fixing image URL: siteCollections -> sites")
    image_url = image_url.replace('/siteCollections/', '/sites/')
```
 
**Fixed URL:**
```
https://graph.microsoft.com/v1.0/sites/{siteId}/onenote/resources/abc123/$value
```
 
### 4c. Download Image
```python
# sync_orchestrator.py line 936-940
response = requests.get(image_url, headers=headers, timeout=30)
return response.content  # Binary image data
```
 
---
 
## Visual Flow Diagram
 
```
📓 desk-notes Notebook
│
├─ STEP 1: GET ALL SECTIONS RECURSIVELY
│  │
│  ├─ API: GET /notebooks/{id}/sections
│  │  └─ Returns: 27 top-level sections
│  │
│  ├─ API: GET /notebooks/{id}/sectionGroups  
│  │  └─ Returns: 25 section groups
│  │
│  └─ For each group (25x):
│     ├─ API: GET /sectionGroups/{groupId}/sections
│     │  └─ Returns: 4-5 sections per group
│     └─ API: GET /sectionGroups/{groupId}/sectionGroups
│        └─ Returns: nested groups (if any)
│
│  RESULT: Flat list of 133 sections ✅
│
├─ STEP 2: GET PAGES FOR EACH SECTION (133x)
│  │
│  ├─ For section "ALPHASENSE":
│  │  └─ API: GET /sections/{sectionId}/pages
│  │     └─ Returns: 12 pages
│  │
│  ├─ For section "Expert Calls" (from AES group):
│  │  └─ API: GET /sections/{sectionId}/pages
│  │     └─ Returns: 8 pages
│  │
│  └─ ... (131 more sections)
│
│  RESULT: ~500 pages total ✅
│
├─ STEP 3: GET CONTENT FOR EACH PAGE (500x)
│  │
│  ├─ For page "AES Q3 2024 Call":
│  │  └─ API: GET /pages/{pageId}/content
│  │     └─ Returns: HTML with text, tables, images
│  │
│  └─ ... (499 more pages)
│
│  RESULT: 500 HTML documents ✅
│
└─ STEP 4: DOWNLOAD IMAGES (1000-2000x)
   │
   ├─ Extract image URLs from HTML
   ├─ Fix URLs (siteCollections → sites)
   ├─ For each image:
   │  └─ API: GET /resources/{resourceId}/$value
   │     └─ Returns: Binary image data
   │
   └─ ... (thousands of images)
 
   RESULT: All images downloaded ✅
```
 
---
 
## Code References
 
### Main Sync Loop
**File:** `backend/services/sync_orchestrator.py`
```python
# Line 147-150: Get all sections recursively
sections = await self._fetch_with_rate_limit(
    self.onenote.list_all_sections_recursive_site_scoped,
    site_id,
    notebook_id
)
 
# Line 153-204: Process each section
for section in sections:
    section_id = section['id']
    section_name = section.get('displayName', 'Unknown')
   
    # Get pages
    pages = await self._fetch_with_rate_limit(
        self.onenote.list_pages_site_scoped,
        site_id,
        section_id
    )
   
    # Process each page
    for page in pages:
        result = await self._sync_page(
            page,
            notebook_id,
            notebook_name,
            section_id,
            section_name,
            site_id=site_id
        )
```
 
### Recursive Section Fetching
**File:** `backend/services/onenote_service.py`
```python
# Line 643-676: Main recursive method
def list_all_sections_recursive_site_scoped(self, site_id: str, notebook_id: str):
    all_sections = []
   
    # 1. Get top-level sections
    top_level = self.list_sections_site_scoped(site_id, notebook_id)
    all_sections.extend(top_level)
   
    # 2. Get section groups
    section_groups = self.list_section_groups_site_scoped(site_id, notebook_id)
   
    # 3. Recursively get sections from each group
    for group in section_groups:
        group_sections = self._get_sections_from_group_recursive_site_scoped(
            site_id, group['id'], group.get('displayName', 'Unknown')
        )
        all_sections.extend(group_sections)
   
    return all_sections
 
# Line 678-706: Recursive helper
def _get_sections_from_group_recursive_site_scoped(self, site_id, group_id, group_name, level=0):
    sections = []
   
    # Get sections in this group
    group_sections = self.list_sections_in_group_site_scoped(site_id, group_id)
    sections.extend(group_sections)
   
    # Get nested groups and recurse
    nested_groups = self.list_nested_groups_site_scoped(site_id, group_id)
    for nested_group in nested_groups:
        nested_sections = self._get_sections_from_group_recursive_site_scoped(
            site_id,
            nested_group['id'],
            nested_group.get('displayName', 'Unknown'),
            level + 1
        )
        sections.extend(nested_sections)
   
    return sections
```
 
---
 
## Key Takeaways
 
### ✅ Yes, Sections First, Then Pages
 
1. **First**: Get ALL sections (recursive through groups)
2. **Then**: For each section, get all pages
3. **Finally**: For each page, get content and images
 
### ✅ Hierarchy is Flattened
 
- Section groups are only used for **discovery**
- The final sections list is **flat** (no hierarchy)
- All sections are treated equally during page sync
 
### ✅ Same Logic for All Sections
 
Once we have the flat list of 133 sections, the sync logic is identical for:
- Top-level sections (ALPHASENSE)
- Sections in groups (Expert Calls)
- The section's origin doesn't matter!
 
### ✅ API Calls Summary
 
For desk-notes (133 sections, ~500 pages):
 
| Step | API Calls | Endpoint |
|------|-----------|----------|
| Get top-level sections | 1 | `/notebooks/{id}/sections` |
| Get section groups | 1 | `/notebooks/{id}/sectionGroups` |
| Get sections per group | 25 | `/sectionGroups/{id}/sections` |
| Get pages per section | 133 | `/sections/{id}/pages` |
| Get page content | ~500 | `/pages/{id}/content` |
| Download images | ~1000-2000 | `/resources/{id}/$value` |
| **TOTAL** | **~1,660-2,660** | |
 
**Time estimate with rate limiting (30 req/min):**
- Initial full sync: **55-88 minutes**
- Incremental syncs: **Much faster** (skips unchanged pages)
 
---
 
## Monitoring the Sync
 
### Backend Logs
```
Found 27 top-level sections
Found 25 section groups to process
  📁 AES: 4 sections
  📁 AKRO NOVO: 4 sections
  📁 AL: 4 sections
  ...
Total sections (including groups): 133
 
Processing section: ALPHASENSE
  Found 12 pages
Processing section: Expert Calls
  Found 8 pages
...
```
 
### Frontend UI
- **Sections discovered**: 133 ✅
- **Pages processed**: 500+ ✅
- **Images downloaded**: 1000+ ✅
- **Progress bar** showing real-time progress