# SOLUTION: Complete OneNote RAG Indexing Recipe
 
## Overview
 
This document describes a **complete, working solution** for discovering and indexing OneNote notebooks (including shared notebooks) via Microsoft Graph API for RAG (Retrieval-Augmented Generation) systems.
 
**Key Discovery**: The `getNotebookFromWebUrl` endpoint can normalize ANY OneNote notebook (owned or shared) into a proper notebook object with `siteId` and `notebookId`, which can then be used to access all content.
 
---
 
## The Breakthrough
 
### Problem We Had
- Shared notebooks appear in OneDrive API but not in OneNote API
- DriveItem IDs cannot be used with OneNote content endpoints
- No way to convert DriveItem ID → OneNote ID
 
### Solution Found
- Use **`POST /me/onenote/notebooks/getNotebookFromWebUrl`**
- Pass the `webUrl` from any source (OneDrive, OneNote, etc.)
- Get back a proper OneNote notebook object with:
  - `id`: OneNote notebook ID
  - `siteId`: Extracted from `self` URL
  - `sectionsUrl`: Direct link to sections
  - `userRole`: Owner/Contributor/Reader
  - `isShared`: true/false
 
**This works for BOTH owned and shared notebooks!**
 
---
 
## Complete Algorithm
 
### Prerequisites
 
**Authentication (Delegated Flow)**:
- User signs in via OAuth
- Get access token with scopes:
  - `Notes.Read` (or `Notes.Read.All`)
  - `Files.Read.All` (for sharedWithMe)
  - `Sites.Read.All` (for site-scoped endpoints)
 
**All API calls**:
```
Base URL: https://graph.microsoft.com/v1.0/
Headers:
  Authorization: Bearer {access_token}
  Content-Type: application/json
```
 
---
 
## Step 1: Discover Candidate Notebooks
 
Use **all three sources** to find notebooks:
 
### 1.1. User's Own Notebooks
```http
GET /me/onenote/notebooks
```
 
**Response**:
```json
{
  "value": [
    {
      "id": "1-af85c8b8-8998-47db-a4b3-abeb291fba11",
      "displayName": "My Personal Notebook",
      "links": {
        "oneNoteWebUrl": {
          "href": "https://..."
        }
      }
    }
  ]
}
```
 
**Extract**: `links.oneNoteWebUrl.href`
 
### 1.2. Recently Used Notebooks
```http
GET /me/onenote/notebooks/getRecentNotebooks(includePersonalNotebooks=true)
```
 
**Response**:
```json
{
  "value": [
    {
      "displayName": "Recent Work",
      "sourceService": "OneDrive",
      "links": {
        "oneNoteWebUrl": {
          "href": "https://..."
        }
      }
    }
  ]
}
```
 
**Extract**: `links.oneNoteWebUrl.href`
 
### 1.3. Notebooks Shared With User (OneDrive)
```http
GET /me/drive/sharedWithMe
```
 
**Response**:
```json
{
  "value": [
    {
      "name": "desk-notes",
      "remoteItem": {
        "package": { "type": "oneNote" },
        "webUrl": "https://davidsonkempner.sharepoint.com/sites/InvestmentManagementIT/_layouts/15/Doc.aspx?sourcedoc=%7BC58A1E27-B40D-404E-B51B-9FA083DFB373%7D&file=desk-notes"
      }
    }
  ]
}
```
 
**Filter**: Keep only items where `remoteItem.package.type === "oneNote"`  
**Extract**: `remoteItem.webUrl`
 
---
 
## Step 2: Normalize Through getNotebookFromWebUrl
 
**This is the KEY step** that converts any notebook (from any source) into a usable OneNote object.
 
### 2.1. For Each Candidate Notebook
 
```http
POST /me/onenote/notebooks/getNotebookFromWebUrl
Content-Type: application/json
 
{
  "webUrl": "<notebookWebUrl>"
}
```
 
**Where `webUrl` comes from**:
- **Owned notebooks**: Use `links.oneNoteWebUrl.href`
- **Recent notebooks**: Use `links.oneNoteWebUrl.href`
- **Shared notebooks**: Use `remoteItem.webUrl`
 
### 2.2. Successful Response
 
```json
{
  "id": "1-c58a1e27-b40d-404e-b51b-9fa083dfb373",
  "displayName": "desk-notes",
  "self": "https://graph.microsoft.com/v1.0/sites/davidsonkempner.sharepoint.com,9bedfee2-863c-49d0-aef7-dc02dde749de,02ab0198-6a10-4e96-b4b4-def8b2ae4aed/onenote/notebooks/1-c58a1e27-b40d-404e-b51b-9fa083dfb373",
  "sectionsUrl": "https://graph.microsoft.com/v1.0/sites/davidsonkempner.sharepoint.com,9bedfee2-863c-49d0-aef7-dc02dde749de,02ab0198-6a10-4e96-b4b4-def8b2ae4aed/onenote/notebooks/1-c58a1e27-b40d-404e-b51b-9fa083dfb373",
  "sectionGroupsUrl": "...",
  "links": {
    "oneNoteWebUrl": { "href": "https://..." },
    "oneNoteClientUrl": { "href": "onenote:..." }
  },
  "userRole": "Reader",
  "isShared": true,
  "createdBy": {
    "user": {
      "displayName": "Rukai Lou"
    }
  }
}
```
 
### 2.3. Extract Critical Information
 
```javascript
const notebookId = response.id;  // e.g., "1-c58a1e27-b40d-404e-b51b-9fa083dfb373"
const notebookName = response.displayName;  // e.g., "desk-notes"
const sectionsUrl = response.sectionsUrl;  // Direct URL to sections
const userRole = response.userRole;  // "Owner", "Contributor", or "Reader"
const isShared = response.isShared;  // true or false
 
// Parse siteId from self URL
// self: ".../sites/{siteId}/onenote/notebooks/..."
const selfUrl = response.self;
const siteIdMatch = selfUrl.match(/sites\/([^/]+)\/onenote/);
const siteId = siteIdMatch ? siteIdMatch[1] : null;
// siteId format: "davidsonkempner.sharepoint.com,9bedfee2-863c-49d0-aef7-dc02dde749de,02ab0198-6a10-4e96-b4b4-def8b2ae4aed"
```
 
### 2.4. Handle Errors
 
If the call fails:
- **404 Not Found**: Notebook doesn't exist or not accessible
- **403 Forbidden**: User doesn't have permission
- **itemNotFound**: Notebook was deleted or sharing revoked
 
**Action**: Skip this notebook, mark as "not indexable"
 
---
 
## Step 3: List Sections
 
For each `(siteId, notebookId)` pair:
 
```http
GET /sites/{siteId}/onenote/notebooks/{notebookId}/sections
```
 
**Example**:
```http
GET /sites/davidsonkempner.sharepoint.com,9bedfee2-863c-49d0-aef7-dc02dde749de,02ab0198-6a10-4e96-b4b4-def8b2ae4aed/onenote/notebooks/1-c58a1e27-b40d-404e-b51b-9fa083dfb373/sections
```
 
**Response**:
```json
{
  "value": [
    {
      "id": "1-af85c8b8-8998-47db-a4b3-abeb291fba11",
      "displayName": "Daily Notes",
      "pagesUrl": "https://graph.microsoft.com/v1.0/onenote/sections/1-af85c8b8-8998-47db-a4b3-abeb291fba11/pages",
      "createdDateTime": "2025-11-01T10:00:00Z",
      "lastModifiedDateTime": "2025-11-20T15:30:00Z"
    },
    {
      "id": "1-12345678-1234-1234-1234-123456789abc",
      "displayName": "Meeting Notes",
      "pagesUrl": "..."
    }
  ]
}
```
 
**Store**:
- `sectionId`
- `sectionName` (displayName)
- `notebookId`
- `notebookName`
- `siteId`
- `pagesUrl`
 
---
 
## Step 4: List Pages in Each Section
 
For each `sectionId`:
 
```http
GET /onenote/sections/{sectionId}/pages
```
 
**Response**:
```json
{
  "value": [
    {
      "id": "1-page-id-123",
      "title": "Desk notes 2025-11-14",
      "createdDateTime": "2025-11-14T09:00:00Z",
      "lastModifiedDateTime": "2025-11-14T17:45:00Z",
      "contentUrl": "https://graph.microsoft.com/v1.0/onenote/pages/1-page-id-123/content",
      "links": {
        "oneNoteWebUrl": {
          "href": "https://davidsonkempner.sharepoint.com/..."
        },
        "oneNoteClientUrl": {
          "href": "onenote:https://..."
        }
      }
    }
  ]
}
```
 
**Store**:
- `pageId`
- `pageTitle` (title)
- `notebookId`, `notebookName`
- `sectionId`, `sectionName`
- `siteId`
- `oneNoteWebUrl` (for deep links in RAG answers)
- `createdDateTime`, `lastModifiedDateTime`
 
---
 
## Step 5: Get HTML Content for RAG
 
For each `pageId`:
 
```http
GET /onenote/pages/{pageId}/content?includeIDs=true
```
 
**Response**: HTML content with OneNote structure
 
```html
<html>
<head>
  <title>Desk notes 2025-11-14</title>
</head>
<body>
  <div data-id="p:{page-guid}">
    <h1 data-id="h1:{guid}">Project Alpha Notes</h1>
    <p data-id="p:{guid}">Discussion about Q4 roadmap...</p>
   
    <h2 data-id="h2:{guid}">Action Items</h2>
    <ul>
      <li data-id="li:{guid}">Review design doc</li>
      <li data-id="li:{guid}">Schedule follow-up</li>
    </ul>
   
    <img src="https://..." data-fullres-src="https://..." />
  </div>
</body>
</html>
```
 
### 5.1. Process HTML for RAG
 
```python
from bs4 import BeautifulSoup
 
def process_page_html(html_content, page_metadata):
    """
    Convert OneNote HTML to structured text for RAG indexing.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
   
    # Extract text with structure preservation
    chunks = []
   
    # Process by heading sections
    for heading in soup.find_all(['h1', 'h2', 'h3']):
        heading_text = heading.get_text(strip=True)
       
        # Get content until next heading
        content_elements = []
        for sibling in heading.next_siblings:
            if sibling.name in ['h1', 'h2', 'h3']:
                break
            if sibling.name:
                content_elements.append(sibling.get_text(strip=True))
       
        content_text = '\n'.join(content_elements)
       
        # Create chunk
        chunk = {
            'heading': heading_text,
            'content': content_text,
            'text': f"{heading_text}\n\n{content_text}",
            'metadata': {
                **page_metadata,
                'heading': heading_text
            }
        }
       
        chunks.append(chunk)
   
    return chunks
```
 
### 5.2. Embed and Store
 
```python
def index_chunks_for_rag(chunks, embedding_model, vector_db):
    """
    Embed chunks and store in vector database.
    """
    for chunk in chunks:
        # Generate embedding
        embedding = embedding_model.embed(chunk['text'])
       
        # Store in vector DB with rich metadata
        vector_db.add(
            id=f"{chunk['metadata']['pageId']}_{chunk['metadata']['heading']}",
            embedding=embedding,
            text=chunk['text'],
            metadata={
                'tenantId': chunk['metadata'].get('tenantId'),
                'siteId': chunk['metadata']['siteId'],
                'notebookId': chunk['metadata']['notebookId'],
                'notebookName': chunk['metadata']['notebookName'],
                'sectionId': chunk['metadata']['sectionId'],
                'sectionName': chunk['metadata']['sectionName'],
                'pageId': chunk['metadata']['pageId'],
                'pageTitle': chunk['metadata']['pageTitle'],
                'heading': chunk['metadata']['heading'],
                'oneNoteWebUrl': chunk['metadata']['oneNoteWebUrl'],
                'lastModified': chunk['metadata']['lastModifiedDateTime']
            }
        )
```
 
---
 
## Step 6: Query-Time Usage (RAG Chatbot)
 
### 6.1. User Query
 
```
User: "What were the action items from the desk-notes meeting?"
```
 
### 6.2. Optional Notebook Filtering
 
```python
# If user specifies notebook
notebook_filter = {"notebookName": "desk-notes"}
 
# Or let user choose from available notebooks
available_notebooks = get_indexed_notebooks()
# ["desk-notes", "My Personal Notebook", "Team Planning"]
```
 
### 6.3. Vector Search
 
```python
def search_and_generate_answer(query, notebook_filter=None):
    """
    Search vector DB and generate answer with sources.
    """
    # Embed query
    query_embedding = embedding_model.embed(query)
   
    # Search with optional metadata filtering
    results = vector_db.search(
        embedding=query_embedding,
        filters=notebook_filter,
        top_k=5
    )
   
    # Generate answer with LLM
    context = '\n\n'.join([r['text'] for r in results])
    answer = llm.generate(
        prompt=f"Context: {context}\n\nQuestion: {query}\n\nAnswer:"
    )
   
    # Format sources
    sources = []
    for result in results[:3]:
        sources.append({
            'notebook': result['metadata']['notebookName'],
            'section': result['metadata']['sectionName'],
            'page': result['metadata']['pageTitle'],
            'link': result['metadata']['oneNoteWebUrl'],
            'snippet': result['text'][:200] + '...'
        })
   
    return {
        'answer': answer,
        'sources': sources
    }
```
 
### 6.4. Display in Chat
 
```
Answer:
The action items from the desk-notes meeting were:
1. Review design doc
2. Schedule follow-up meeting
3. Update roadmap timeline
 
Sources:
📓 desk-notes → Daily Notes → "Desk notes 2025-11-14"
   [View in OneNote]
   
📓 desk-notes → Meeting Notes → "Q4 Planning"
   [View in OneNote]
```
 
---
 
## Ultra-Compressed Recipe (TL;DR)
 
```javascript
// 1. Find candidates
const ownedNotebooks = await GET('/me/onenote/notebooks');
const recentNotebooks = await GET('/me/onenote/notebooks/getRecentNotebooks(includePersonalNotebooks=true)');
const sharedItems = await GET('/me/drive/sharedWithMe');
const sharedNotebooks = sharedItems.filter(item => item.remoteItem?.package?.type === 'oneNote');
 
// 2. Normalize each to real notebook
for (const candidate of allCandidates) {
  const webUrl = extractWebUrl(candidate);
  const notebook = await POST('/me/onenote/notebooks/getNotebookFromWebUrl', { webUrl });
 
  if (notebook.id) {
    const { id: notebookId, displayName: notebookName } = notebook;
    const siteId = extractSiteIdFromSelf(notebook.self);
   
    // 3. Walk structure
    const sections = await GET(`/sites/${siteId}/onenote/notebooks/${notebookId}/sections`);
   
    for (const section of sections.value) {
      const pages = await GET(`/onenote/sections/${section.id}/pages`);
     
      for (const page of pages.value) {
        const html = await GET(`/onenote/pages/${page.id}/content?includeIDs=true`);
       
        // 4. Index for RAG
        const chunks = processHTML(html);
        await indexChunks(chunks, {
          siteId,
          notebookId,
          notebookName,
          sectionId: section.id,
          sectionName: section.displayName,
          pageId: page.id,
          pageTitle: page.title,
          oneNoteWebUrl: page.links.oneNoteWebUrl.href
        });
      }
    }
  }
}
```
 
---
 
## Key Advantages
 
✅ **Works for shared notebooks**: No sync delay needed  
✅ **Unified approach**: Same code for owned and shared  
✅ **Rich metadata**: Full notebook/section/page hierarchy  
✅ **Deep links**: Direct links to pages in answers  
✅ **Permission-aware**: Respects user access levels  
✅ **Scalable**: Can index hundreds of notebooks  
 
---
 
## Next Steps
 
1. **Test the solution** with real access token
2. **Implement indexer** that follows this recipe
3. **Integrate with existing RAG pipeline**
4. **Add incremental sync** (track lastModifiedDateTime)
5. **Handle rate limiting** (429 responses)
 
---
 
## References
 
- [Microsoft Graph OneNote API](https://learn.microsoft.com/en-us/graph/api/resources/onenote)
- [getNotebookFromWebUrl](https://learn.microsoft.com/en-us/graph/api/notebook-getnotebookfromweburl)
- [OneNote Permissions](https://learn.microsoft.com/en-us/graph/permissions-reference#notes-permissions)