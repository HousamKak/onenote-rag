# Production Requirements: C# Backend with MCP Server

This document outlines the requirements for productionizing the OneNote RAG system with a C# backend, using the MCP (Model Context Protocol) server for OneNote integration instead of RAG capabilities.

## Overview

The production version simplifies the current Python RAG system by:
- Replacing Python/FastAPI with C#/ASP.NET Core
- Using MCP server for OneNote access (instead of direct Microsoft Graph API)
- Removing RAG capabilities (no vector database, embeddings, or LLM processing)
- Focusing on direct OneNote CRUD operations and search

---

## 1. Backend Requirements (C# .NET)

### Core Stack
- **.NET 8.0+** (Latest LTS version)
- **ASP.NET Core Web API** for REST endpoints
- **MCP SDK** - Model Context Protocol client integration

### Key NuGet Packages

```xml
<PackageReference Include="Microsoft.AspNetCore.OpenApi" />
<PackageReference Include="Swashbuckle.AspNetCore" /> <!-- API documentation -->
<PackageReference Include="Microsoft.Extensions.Logging" />
<PackageReference Include="Microsoft.Extensions.Caching.Memory" /> <!-- Performance -->
<PackageReference Include="System.Text.Json" /> <!-- or Newtonsoft.Json -->
```

### MCP Integration
- **MCP Client Library** - Connect to the azure-onenote MCP server
- The MCP server handles all OneNote operations (no need for Microsoft Graph SDK directly)
- MCP Server URL: https://mcpmarket.com/server/azure-onenote

---

## 2. Feature Migration Map

### From Python to C# (Simplified)

| Python Component | C# Equivalent | Notes |
|---|---|---|
| `onenote_service.py` | **MCP Client calls** | Replace Graph API with MCP server calls |
| `api/routes.py` | **ASP.NET Controllers** | RESTful API endpoints |
| `models/document.py` | **C# DTOs/Models** | Data Transfer Objects |
| `document_processor.py` | **Not needed** | No chunking required |
| `vector_store.py` | **Not needed** | No vector database |
| `rag_engine.py` | **Not needed** | No RAG processing |
| `rag_techniques.py` | **Not needed** | No advanced techniques |
| Vector DB (ChromaDB) | **Not needed** | Skip ChromaDB, embeddings, LangChain |
| LangSmith tracking | **Optional logging** | Use Serilog or built-in logging |

---

## 3. API Endpoints to Implement

### Health & Configuration
```
GET  /api/health                 # Health check endpoint
GET  /api/config                 # Get application configuration
```

### OneNote Operations (via MCP Server)
```
GET  /api/notebooks              # List all notebooks
GET  /api/notebooks/{id}/sections # List sections in a notebook
GET  /api/sections/{id}/pages     # List pages in a section
GET  /api/pages/{id}              # Get page content (HTML)
POST /api/pages                   # Create a new page
PUT  /api/pages/{id}              # Update page content
DELETE /api/pages/{id}            # Delete a page
GET  /api/search?q={query}        # Search across all notebooks
```

### Response Models

```csharp
public class NotebookDto
{
    public string Id { get; set; }
    public string DisplayName { get; set; }
    public DateTime CreatedDateTime { get; set; }
    public DateTime LastModifiedDateTime { get; set; }
}

public class SectionDto
{
    public string Id { get; set; }
    public string DisplayName { get; set; }
    public string NotebookId { get; set; }
}

public class PageDto
{
    public string Id { get; set; }
    public string Title { get; set; }
    public string Content { get; set; } // HTML content
    public string SectionId { get; set; }
    public DateTime CreatedDateTime { get; set; }
    public DateTime LastModifiedDateTime { get; set; }
    public string WebUrl { get; set; }
}

public class SearchResultDto
{
    public List<PageDto> Pages { get; set; }
    public int TotalResults { get; set; }
    public string Query { get; set; }
}
```

---

## 4. Authentication & Security

### Required Security Features

1. **Azure AD Authentication** for MCP server
   - Client ID, Client Secret, Tenant ID (same as current Python version)
   
2. **JWT Tokens** for API authentication (if exposing publicly)

3. **CORS Configuration** for frontend access

4. **Rate Limiting** middleware to prevent abuse

5. **API Versioning** (e.g., `/api/v1/...`)

6. **Input Validation** using FluentValidation or Data Annotations

### Configuration (appsettings.json)

```json
{
  "AzureAd": {
    "TenantId": "your-tenant-id",
    "ClientId": "your-client-id",
    "ClientSecret": "your-client-secret"
  },
  "McpServer": {
    "Endpoint": "https://your-mcp-server-endpoint",
    "Timeout": 30
  },
  "Cors": {
    "AllowedOrigins": [
      "http://localhost:5173",
      "https://your-production-domain.com"
    ]
  },
  "RateLimiting": {
    "PermitLimit": 100,
    "Window": "00:01:00"
  },
  "Logging": {
    "LogLevel": {
      "Default": "Information",
      "Microsoft.AspNetCore": "Warning"
    }
  }
}
```

### Security Packages

```xml
<PackageReference Include="Microsoft.Identity.Web" />
<PackageReference Include="AspNetCoreRateLimit" />
<PackageReference Include="FluentValidation.AspNetCore" />
```

---

## 5. Frontend Requirements

### Keep from Current React/TypeScript App
- `IndexPage.tsx` → Rename to **"Browse"** page (list/view notebooks, sections, pages)
- `ChatPage.tsx` → **"Chat"** interface (simple Q&A, no RAG)
- All UI components:
  - `Layout.tsx`
  - `Sidebar.tsx`
  - `ChatSidebar.tsx`
  - `ThemeSwitcher.tsx`
  - `NotificationModal.tsx`
  - `ConfirmModal.tsx`

### Remove from Current App
- ❌ `ConfigPage.tsx` - RAG configuration not needed
- ❌ `ComparePage.tsx` - No config comparison
- ❌ `QueryPage.tsx` - Replace with simple search
- ❌ RAG technique toggles
- ❌ Vector DB statistics
- ❌ Advanced settings UI

### New/Updated Components Needed

1. **SearchPage.tsx** - Simple OneNote search interface
2. **PageViewer.tsx** - Display OneNote page content
3. **PageEditor.tsx** - Create/edit OneNote pages
4. **NotebookBrowser.tsx** - Tree view of notebooks/sections/pages

### Updated API Client

```typescript
// src/api/client.ts
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// OneNote operations
export const oneNoteApi = {
  // Notebooks
  getNotebooks: () => 
    api.get<NotebookDto[]>('/notebooks'),
  
  // Sections
  getSections: (notebookId: string) => 
    api.get<SectionDto[]>(`/notebooks/${notebookId}/sections`),
  
  // Pages
  getPages: (sectionId: string) => 
    api.get<PageDto[]>(`/sections/${sectionId}/pages`),
  
  getPage: (pageId: string) => 
    api.get<PageDto>(`/pages/${pageId}`),
  
  createPage: (data: CreatePageRequest) => 
    api.post<PageDto>('/pages', data),
  
  updatePage: (pageId: string, data: UpdatePageRequest) => 
    api.put<PageDto>(`/pages/${pageId}`, data),
  
  deletePage: (pageId: string) => 
    api.delete(`/pages/${pageId}`),
  
  // Search
  search: (query: string) => 
    api.get<SearchResultDto>(`/search?q=${encodeURIComponent(query)}`),
};

// Health check
export const healthCheck = () => api.get('/health');
```

---

## 6. Infrastructure & Deployment

### Azure Resources Required

1. **Azure App Service** or **Azure Container Apps**
   - Hosting for C# backend
   - Linux or Windows plan (.NET 8)
   - Scaling: Start with B1 (Basic), scale to S1+ (Standard) for production

2. **Azure Key Vault**
   - Store secrets securely (client secrets, API keys)
   - Integrate with App Service using Managed Identity

3. **Application Insights**
   - Monitoring and logging
   - Performance metrics
   - Error tracking
   - Custom telemetry

4. **Azure Static Web Apps** or **Azure CDN**
   - Frontend hosting (React app)
   - Global distribution
   - SSL/HTTPS automatic

5. **Azure API Management** (Optional)
   - API gateway
   - Rate limiting
   - Analytics
   - Developer portal

### CI/CD Pipeline

**GitHub Actions Workflow** (`.github/workflows/deploy.yml`):

```yaml
name: Deploy to Azure

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    # Backend
    - name: Setup .NET
      uses: actions/setup-dotnet@v3
      with:
        dotnet-version: '8.0.x'
    
    - name: Build backend
      run: dotnet build --configuration Release
    
    - name: Run tests
      run: dotnet test --no-build --verbosity normal
    
    - name: Publish backend
      run: dotnet publish -c Release -o ./publish
    
    - name: Deploy to Azure App Service
      uses: azure/webapps-deploy@v2
      with:
        app-name: 'onenote-api'
        publish-profile: ${{ secrets.AZURE_WEBAPP_PUBLISH_PROFILE }}
        package: ./publish
    
    # Frontend
    - name: Setup Node.js
      uses: actions/setup-node@v3
      with:
        node-version: '18'
    
    - name: Install frontend dependencies
      working-directory: ./frontend
      run: npm ci
    
    - name: Build frontend
      working-directory: ./frontend
      run: npm run build
      env:
        VITE_API_URL: ${{ secrets.API_URL }}
    
    - name: Deploy frontend to Static Web Apps
      uses: Azure/static-web-apps-deploy@v1
      with:
        azure_static_web_apps_api_token: ${{ secrets.AZURE_STATIC_WEB_APPS_API_TOKEN }}
        repo_token: ${{ secrets.GITHUB_TOKEN }}
        action: "upload"
        app_location: "./frontend"
        output_location: "dist"
```

### Environment Configuration

**Development:**
- Local IIS Express or Kestrel
- Local SQL Server (if needed)
- Development App Registration

**Staging:**
- Azure App Service (Staging slot)
- Staging Key Vault
- Staging App Registration

**Production:**
- Azure App Service (Production slot)
- Production Key Vault
- Production App Registration
- Blue-Green deployment strategy

---

## 7. Removed Components (Not Needed)

### Python Dependencies No Longer Required

❌ **ChromaDB** - No vector database needed  
❌ **OpenAI API** - No LLM calls  
❌ **LangChain** - No RAG framework  
❌ **LangSmith** - No tracing (use Application Insights instead)  
❌ **Cohere** - No re-ranking  
❌ **FAISS** - No similarity search  
❌ **Sentence Transformers** - No embeddings  

### Services Removed

- `document_processor.py` - No text chunking
- `vector_store.py` - No vector storage
- `rag_engine.py` - No RAG processing
- `rag_techniques.py` - No advanced techniques

### Frontend Features Removed

- RAG configuration interface
- Technique toggles (Multi-Query, RAG-Fusion, etc.)
- Configuration comparison
- Vector database statistics
- Preset selection (Fast, Balanced, Quality, Research)
- Performance metrics related to RAG

---

## 8. Sample C# Project Structure

```
OneNoteAPI/
├── OneNoteAPI.sln
├── src/
│   ├── OneNoteAPI/
│   │   ├── Controllers/
│   │   │   ├── NotebooksController.cs
│   │   │   ├── SectionsController.cs
│   │   │   ├── PagesController.cs
│   │   │   └── SearchController.cs
│   │   ├── Services/
│   │   │   ├── IMcpClient.cs
│   │   │   ├── McpClient.cs
│   │   │   └── CacheService.cs
│   │   ├── Models/
│   │   │   ├── DTOs/
│   │   │   │   ├── NotebookDto.cs
│   │   │   │   ├── SectionDto.cs
│   │   │   │   ├── PageDto.cs
│   │   │   │   └── SearchResultDto.cs
│   │   │   └── Requests/
│   │   │       ├── CreatePageRequest.cs
│   │   │       └── UpdatePageRequest.cs
│   │   ├── Middleware/
│   │   │   ├── ErrorHandlingMiddleware.cs
│   │   │   └── RequestLoggingMiddleware.cs
│   │   ├── Configuration/
│   │   │   ├── AzureAdOptions.cs
│   │   │   └── McpServerOptions.cs
│   │   ├── Program.cs
│   │   └── appsettings.json
├── tests/
│   ├── OneNoteAPI.UnitTests/
│   │   ├── Controllers/
│   │   └── Services/
│   └── OneNoteAPI.IntegrationTests/
│       └── Api/
└── README.md
```

---

## 9. Sample Controller Implementation

```csharp
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Caching.Memory;

namespace OneNoteAPI.Controllers;

[ApiController]
[Route("api/v1/[controller]")]
[ApiVersion("1.0")]
public class NotebooksController : ControllerBase
{
    private readonly IMcpClient _mcpClient;
    private readonly ILogger<NotebooksController> _logger;
    private readonly IMemoryCache _cache;

    public NotebooksController(
        IMcpClient mcpClient, 
        ILogger<NotebooksController> logger,
        IMemoryCache cache)
    {
        _mcpClient = mcpClient;
        _logger = logger;
        _cache = cache;
    }

    /// <summary>
    /// Get all notebooks
    /// </summary>
    /// <returns>List of notebooks</returns>
    [HttpGet]
    [ProducesResponseType(typeof(IEnumerable<NotebookDto>), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status500InternalServerError)]
    public async Task<IActionResult> GetNotebooks()
    {
        try
        {
            const string cacheKey = "notebooks_list";
            
            if (!_cache.TryGetValue(cacheKey, out IEnumerable<NotebookDto>? notebooks))
            {
                _logger.LogInformation("Fetching notebooks from MCP server");
                notebooks = await _mcpClient.ListNotebooksAsync();
                
                var cacheOptions = new MemoryCacheEntryOptions()
                    .SetAbsoluteExpiration(TimeSpan.FromMinutes(5));
                
                _cache.Set(cacheKey, notebooks, cacheOptions);
            }
            else
            {
                _logger.LogInformation("Retrieved notebooks from cache");
            }

            return Ok(notebooks);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error retrieving notebooks");
            return StatusCode(500, new { message = "Error retrieving notebooks" });
        }
    }

    /// <summary>
    /// Get sections in a notebook
    /// </summary>
    /// <param name="id">Notebook ID</param>
    /// <returns>List of sections</returns>
    [HttpGet("{id}/sections")]
    [ProducesResponseType(typeof(IEnumerable<SectionDto>), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    [ProducesResponseType(StatusCodes.Status500InternalServerError)]
    public async Task<IActionResult> GetSections(string id)
    {
        try
        {
            _logger.LogInformation("Fetching sections for notebook {NotebookId}", id);
            var sections = await _mcpClient.ListSectionsAsync(id);
            
            if (sections == null || !sections.Any())
            {
                return NotFound(new { message = $"No sections found for notebook {id}" });
            }

            return Ok(sections);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error retrieving sections for notebook {NotebookId}", id);
            return StatusCode(500, new { message = "Error retrieving sections" });
        }
    }
}
```

---

## 10. Testing Strategy

### Unit Tests

**Test Framework:** xUnit or NUnit

**Coverage Areas:**
- Controller logic
- MCP client wrapper methods
- Data model validation
- Business logic

**Mocking:** Use Moq for dependencies

**Example:**

```csharp
public class NotebooksControllerTests
{
    private readonly Mock<IMcpClient> _mcpClientMock;
    private readonly Mock<ILogger<NotebooksController>> _loggerMock;
    private readonly Mock<IMemoryCache> _cacheMock;
    private readonly NotebooksController _controller;

    public NotebooksControllerTests()
    {
        _mcpClientMock = new Mock<IMcpClient>();
        _loggerMock = new Mock<ILogger<NotebooksController>>();
        _cacheMock = new Mock<IMemoryCache>();
        
        _controller = new NotebooksController(
            _mcpClientMock.Object,
            _loggerMock.Object,
            _cacheMock.Object
        );
    }

    [Fact]
    public async Task GetNotebooks_ReturnsOkResult_WithNotebooks()
    {
        // Arrange
        var expectedNotebooks = new List<NotebookDto>
        {
            new() { Id = "1", DisplayName = "Test Notebook" }
        };
        
        _mcpClientMock
            .Setup(x => x.ListNotebooksAsync())
            .ReturnsAsync(expectedNotebooks);

        // Act
        var result = await _controller.GetNotebooks();

        // Assert
        var okResult = Assert.IsType<OkObjectResult>(result);
        var notebooks = Assert.IsAssignableFrom<IEnumerable<NotebookDto>>(okResult.Value);
        Assert.Single(notebooks);
    }
}
```

### Integration Tests

**Test Areas:**
- API endpoint functionality
- MCP server connectivity
- Authentication flow
- End-to-end workflows

**Use WebApplicationFactory for in-memory testing:**

```csharp
public class NotebooksApiTests : IClassFixture<WebApplicationFactory<Program>>
{
    private readonly HttpClient _client;

    public NotebooksApiTests(WebApplicationFactory<Program> factory)
    {
        _client = factory.CreateClient();
    }

    [Fact]
    public async Task Get_Notebooks_Returns_Success()
    {
        // Act
        var response = await _client.GetAsync("/api/v1/notebooks");

        // Assert
        response.EnsureSuccessStatusCode();
        var content = await response.Content.ReadAsStringAsync();
        Assert.NotEmpty(content);
    }
}
```

### Testing Tools

```xml
<PackageReference Include="xUnit" Version="2.6.0" />
<PackageReference Include="Moq" Version="4.20.0" />
<PackageReference Include="FluentAssertions" Version="6.12.0" />
<PackageReference Include="Microsoft.AspNetCore.Mvc.Testing" Version="8.0.0" />
<PackageReference Include="Testcontainers" Version="3.6.0" /> <!-- If needed -->
```

---

## 11. Comparison: Python vs C# Version

| Aspect | Python RAG Version | C# Production Version |
|---|---|---|
| **Backend Framework** | Python + FastAPI | C# + ASP.NET Core 8 |
| **OneNote Access** | Direct Microsoft Graph API | MCP Server (abstracted) |
| **Intelligence Layer** | RAG with embeddings & LLM | Simple search only |
| **Database** | ChromaDB (Vector DB) | None (direct OneNote access) |
| **Services** | 7 services (RAG, Vector, etc.) | 2-3 services (MCP client, Cache) |
| **Dependencies** | 20+ Python packages | 5-8 NuGet packages |
| **Complexity** | High (RAG pipeline) | Low (CRUD operations) |
| **Response Time** | 1-15s (depending on preset) | <500ms (direct queries) |
| **Cost per Query** | $0.01-$0.08 (LLM costs) | Negligible (API calls only) |
| **Deployment** | Uvicorn + Docker | IIS / Kestrel |
| **Authentication** | MSAL + OAuth | Azure AD + JWT |
| **Monitoring** | LangSmith + Logging | Application Insights |
| **Scalability** | Limited (LLM rate limits) | High (stateless API) |

---

## 12. Migration Checklist

### Phase 1: Backend Setup (Week 1-2)
- [ ] Create .NET 8 Web API project
- [ ] Set up solution structure (Controllers, Services, Models)
- [ ] Configure Azure AD authentication
- [ ] Integrate MCP client library
- [ ] Implement NotebooksController
- [ ] Implement SectionsController
- [ ] Implement PagesController
- [ ] Implement SearchController
- [ ] Add error handling middleware
- [ ] Add logging (Serilog or built-in)
- [ ] Configure CORS
- [ ] Add API versioning
- [ ] Set up Swagger/OpenAPI docs
- [ ] Write unit tests for controllers

### Phase 2: Azure Integration (Week 2-3)
- [ ] Set up Azure App Service
- [ ] Configure Key Vault for secrets
- [ ] Set up Application Insights
- [ ] Configure Managed Identity
- [ ] Test MCP server connectivity
- [ ] Set up staging environment
- [ ] Configure CI/CD pipeline (GitHub Actions)
- [ ] Implement rate limiting
- [ ] Add caching layer (Redis or Memory)

### Phase 3: Frontend Updates (Week 3-4)
- [ ] Update API client (remove RAG endpoints)
- [ ] Simplify UI (remove config pages)
- [ ] Create NotebookBrowser component
- [ ] Create PageViewer component
- [ ] Create PageEditor component
- [ ] Update SearchPage (simple search)
- [ ] Test all CRUD operations
- [ ] Update routing
- [ ] Deploy to Azure Static Web Apps

### Phase 4: Testing & Documentation (Week 4)
- [ ] Integration testing (API + MCP)
- [ ] Load testing (Apache JMeter or k6)
- [ ] Security audit (OWASP checks)
- [ ] Performance optimization
- [ ] Update README.md
- [ ] Create API documentation
- [ ] User acceptance testing (UAT)
- [ ] Final deployment to production

---

## 13. Performance Expectations

### Response Times (Target)
- **List notebooks:** < 200ms
- **List sections:** < 150ms
- **List pages:** < 300ms
- **Get page content:** < 500ms
- **Search:** < 1s
- **Create/Update page:** < 800ms

### Scalability
- **Concurrent users:** 100+ (with caching)
- **Requests per second:** 50+ (API Gateway can scale higher)
- **Database:** Not applicable (OneNote handles storage)

### Caching Strategy
- **Notebooks list:** Cache for 5 minutes
- **Sections list:** Cache for 3 minutes
- **Pages list:** Cache for 2 minutes
- **Page content:** Cache for 1 minute (or invalidate on update)

---

## 14. Security Considerations

### API Security
1. **Authentication:** Azure AD JWT tokens required for all endpoints
2. **Authorization:** Role-based access control (RBAC)
3. **Rate Limiting:** 100 requests per minute per user
4. **Input Validation:** Sanitize all user inputs
5. **HTTPS Only:** Enforce SSL/TLS
6. **CORS:** Whitelist specific origins only

### Secret Management
- Store all secrets in **Azure Key Vault**
- Use **Managed Identity** for Key Vault access
- Never commit secrets to source control
- Rotate secrets regularly (90 days)

### Compliance
- **GDPR:** Handle user data appropriately
- **Data Residency:** OneNote data stays in Microsoft's cloud
- **Audit Logging:** Log all data access via Application Insights

---

## 15. Cost Estimation (Monthly)

### Azure Resources (Estimated)

| Resource | Tier | Monthly Cost |
|---|---|---|
| App Service (B1 Basic) | 1 instance | ~$13 |
| Application Insights | 5GB data | ~$10 |
| Key Vault | 10,000 operations | ~$3 |
| Static Web Apps | Free tier | $0 |
| **Total (Development)** | | **~$26/month** |

### Production Scaling

| Resource | Tier | Monthly Cost |
|---|---|---|
| App Service (S1 Standard) | 2 instances | ~$146 |
| Application Insights | 50GB data | ~$115 |
| Key Vault | 100,000 operations | ~$5 |
| Azure CDN | 100GB transfer | ~$8 |
| **Total (Production)** | | **~$274/month** |

**Note:** No LLM costs (OpenAI, Cohere) since RAG is removed.

---

## 16. Next Steps

### Immediate Actions
1. **Review this document** with tech lead for approval
2. **Set up Azure resources** (App Service, Key Vault, etc.)
3. **Create MCP server account** and test connectivity
4. **Initialize .NET project** with recommended structure
5. **Set up version control** and CI/CD pipeline

### First Sprint Goals
- Basic API with health check
- OneNote notebooks listing (via MCP)
- Simple frontend to display notebooks
- Deployed to Azure staging environment

### Questions to Resolve
- [ ] Who will manage Azure subscriptions and resource groups?
- [ ] What authentication model for end users? (Azure AD B2C? Custom?)
- [ ] Should we add SQL database for caching/analytics?
- [ ] Do we need real-time updates? (SignalR integration?)
- [ ] What's the timeline for MVP vs full production?

---

## 17. Resources & References

### MCP Server
- **MCP Market:** https://mcpmarket.com/server/azure-onenote
- **Azure OneNote MCP Server** - Available as separate component
- **MCP Documentation:** https://modelcontextprotocol.io/docs/getting-started/intro

### .NET Resources
- **ASP.NET Core Docs:** https://learn.microsoft.com/aspnet/core
- **.NET 8 Release:** https://dotnet.microsoft.com/download/dotnet/8.0
- **Web API Tutorial:** https://learn.microsoft.com/aspnet/core/tutorials/first-web-api

### Azure Resources
- **App Service Docs:** https://learn.microsoft.com/azure/app-service/
- **Key Vault Docs:** https://learn.microsoft.com/azure/key-vault/
- **Application Insights:** https://learn.microsoft.com/azure/azure-monitor/app/app-insights-overview

### Testing
- **xUnit:** https://xunit.net/
- **Moq:** https://github.com/moq/moq4
- **FluentAssertions:** https://fluentassertions.com/

---

## Conclusion

This production version significantly simplifies the architecture by removing RAG capabilities and focusing on direct OneNote integration via the MCP server. The C# backend provides:

✅ **Simplicity** - No complex RAG pipeline  
✅ **Performance** - Sub-second response times  
✅ **Scalability** - Stateless API design  
✅ **Cost-Effective** - No LLM costs  
✅ **Maintainable** - Standard .NET patterns  
✅ **Production-Ready** - Azure native integration  

The system can be extended later to add RAG capabilities if needed, but starts with a solid foundation for OneNote CRUD operations and search.

---

**Document Version:** 1.0  
**Last Updated:** November 4, 2025  
**Author:** Technical Team  
**Status:** Ready for Review
