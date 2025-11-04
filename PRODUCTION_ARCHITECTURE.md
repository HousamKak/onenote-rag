# Production Architecture Plan

## 1. How We're Building This for Production

### Core Architecture Pattern: Plugin System

**Single Interface Contract**
```csharp
public interface IDocumentSource
{
    string SourceType { get; }
    SourceCapabilities Capabilities { get; }

    Task<IEnumerable<SourceDocument>> GetAllDocumentsAsync(FetchOptions options);
    Task<SourceDocument?> GetDocumentAsync(string documentId);
    Task<McpResponse> ExecuteMcpQueryAsync(McpRequest request);
}

public class SourceCapabilities
{
    public bool SupportsMcp { get; set; }
    public bool SupportsRag { get; set; }
}
```

**Automatic Plugin Discovery**
```csharp
// In Startup.cs
services.DiscoverAndRegisterPlugins(); // Scans assemblies for IDocumentSource implementations
services.AddScoped<IQueryEngine, QueryEngine>();
services.AddScoped<IStrategySelector, StrategySelector>();
```

**How It Works**
1. Each data source is a separate plugin implementing `IDocumentSource`
2. Plugins declare their capabilities (MCP support, RAG support)
3. Application auto-discovers plugins at startup via reflection
4. Strategy selector routes queries to MCP or RAG based on capabilities

---

## 2. Multiple Sources & Techniques (MCP + RAG)

### Auto-Selection Strategy

```csharp
public class StrategySelector : IStrategySelector
{
    public IQueryStrategy SelectStrategy(QueryRequest request, IDocumentSource source)
    {
        var caps = source.Capabilities;

        // User preference override
        if (request.PreferredMode == QueryMode.Mcp && caps.SupportsMcp)
            return _mcpStrategy;
        if (request.PreferredMode == QueryMode.Rag && caps.SupportsRag)
            return _ragStrategy;

        // Auto-selection heuristics
        if (IsSimpleLookup(request.Query) && caps.SupportsMcp)
            return _mcpStrategy;  // Fast, direct lookup

        if (IsComplexQuery(request.Query) && caps.SupportsRag)
            return _ragStrategy;  // Semantic search

        // Fallback to available option
        return caps.SupportsMcp ? _mcpStrategy : _ragStrategy;
    }

    private bool IsSimpleLookup(string query) =>
        query.StartsWith("get ", StringComparison.OrdinalIgnoreCase) ||
        query.StartsWith("show ", StringComparison.OrdinalIgnoreCase) ||
        query.StartsWith("find document ", StringComparison.OrdinalIgnoreCase);

    private bool IsComplexQuery(string query) =>
        query.Contains("summarize", StringComparison.OrdinalIgnoreCase) ||
        query.Contains("analyze", StringComparison.OrdinalIgnoreCase) ||
        query.Contains("compare", StringComparison.OrdinalIgnoreCase);
}
```

### Plugin Examples

**OneNote Plugin (MCP + RAG)**
```csharp
public class OneNoteAdapter : IDocumentSource
{
    private readonly IMcpClient _mcpClient;

    public string SourceType => "onenote";
    public SourceCapabilities Capabilities => new()
    {
        SupportsMcp = true,   // Has MCP server
        SupportsRag = true    // Can also do semantic search
    };

    public async Task<McpResponse> ExecuteMcpQueryAsync(McpRequest request)
    {
        // Direct MCP call to @modelcontextprotocol/server-onenote
        return await _mcpClient.SendRequestAsync(request);
    }

    public async Task<IEnumerable<SourceDocument>> GetAllDocumentsAsync(FetchOptions options)
    {
        // Fetch via MCP for indexing into vector store
        var notebooks = await _mcpClient.SendRequestAsync(new McpRequest
        {
            Method = "tools/call",
            Params = new { name = "list_notebooks" }
        });
        // Convert to SourceDocument objects
    }
}
```

**SQL Database Plugin (RAG Only)**
```csharp
public class SqlDatabaseAdapter : IDocumentSource
{
    public string SourceType => "sql-database";
    public SourceCapabilities Capabilities => new()
    {
        SupportsMcp = false,  // No MCP server available
        SupportsRag = true    // Use RAG for text-to-SQL
    };

    public async Task<IEnumerable<SourceDocument>> GetAllDocumentsAsync(FetchOptions options)
    {
        // Build documents from database schema
        var schema = await _dbContext.GetSchemaAsync();
        return schema.Tables.Select(table => new SourceDocument
        {
            Id = $"table:{table.Name}",
            Content = $"Table: {table.Name}\nColumns: {string.Join(", ", table.Columns)}",
            Metadata = new { TableName = table.Name, RowCount = table.RowCount }
        });
    }

    // ExecuteMcpQueryAsync throws NotSupportedException
}
```

**Confluence Plugin (MCP + RAG)**
```csharp
public class ConfluenceAdapter : IDocumentSource
{
    public string SourceType => "confluence";
    public SourceCapabilities Capabilities => new()
    {
        SupportsMcp = true,   // @modelcontextprotocol/server-confluence
        SupportsRag = true
    };
    // Implementation similar to OneNote
}
```

### Query Flow

```
User Query → Strategy Selector → Decision:
                                   ├─ MCP Available + Simple Query → MCP Client → Data Source
                                   └─ RAG Required + Complex Query → RAG Engine → Vector Store → LLM
```

**MCP Flow** (Fast: <500ms)
1. Parse query
2. Send JSON-RPC request to MCP server via STDIO
3. Return structured response
4. Format for user

**RAG Flow** (Intelligent: 2-10s)
1. Generate embeddings for query
2. Vector similarity search (Azure AI Search)
3. Apply RAG technique (Multi-Query, RAG-Fusion, HyDE, etc.)
4. Re-rank results (Cohere)
5. Generate answer with LLM (GPT-4)

---

## 3. Technology Stack

### Backend (C# .NET 8)
```
RagPlatform.sln
├── RagPlatform.Core/              # Interfaces, models, abstractions
│   ├── IDocumentSource.cs
│   ├── IQueryStrategy.cs
│   ├── IStrategySelector.cs
│   └── SourceCapabilities.cs
├── RagPlatform.Api/               # ASP.NET Core 8 Web API
│   ├── Controllers/QueryController.cs
│   └── Program.cs
├── RagPlatform.Infrastructure/    # Azure services, MCP clients
│   ├── Mcp/StdioMcpClient.cs
│   ├── Rag/RagEngine.cs
│   ├── VectorStore/AzureAiSearchService.cs
│   └── Azure/CosmosDbRepository.cs
└── RagPlatform.Plugins/           # Data source plugins
    ├── OneNoteAdapter.cs
    ├── SqlDatabaseAdapter.cs
    └── ConfluenceAdapter.cs
```

**Key NuGet Packages**
- `Microsoft.AspNetCore.App` (8.0)
- `Azure.AI.OpenAI` - LLM and embeddings
- `Azure.Search.Documents` - Vector store
- `Azure.Cosmos` - Multi-tenant data storage
- `StackExchange.Redis` - Caching
- `Azure.Messaging.ServiceBus` - Async processing
- `Microsoft.Identity.Web` - Azure AD authentication

### Frontend (React + TypeScript)
- Existing React 18 + Vite setup
- Minor updates to support multiple sources
- Source selector dropdown in UI

### Cloud Infrastructure (Azure)
| Service | Purpose | Monthly Cost |
|---------|---------|--------------|
| **Azure App Service** (P1v3) | Host .NET API | ~$146 |
| **Azure Cosmos DB** | Multi-tenant document storage | ~$400 |
| **Azure AI Search** (S1) | Vector store (HNSW algorithm) | ~$250 |
| **Azure OpenAI** | GPT-4 + embeddings | ~$3,000-3,500 |
| **Azure Redis Cache** (C1) | Query caching | ~$57 |
| **Azure Service Bus** (Standard) | Message queue | ~$10 |
| **Application Insights** | Monitoring | ~$100-150 |
| **Azure Storage** (GPv2) | Blobs, logs | ~$50 |
| **TOTAL** | | **~$4,100-4,600/month** |

### MCP Integration
- **Protocol**: JSON-RPC over STDIO (standard input/output)
- **Supported MCP Servers**:
  - `@modelcontextprotocol/server-onenote` (Node.js)
  - `@modelcontextprotocol/server-confluence` (Node.js)
  - Custom Python/Node.js MCP servers
- **Connection Pooling**: Reuse process connections
- **Process Management**: Supervisor pattern for MCP server lifecycle

### Development & Deployment
- **IaC**: Terraform (all Azure resources)
- **CI/CD**: GitHub Actions
- **Environments**: Dev, Staging, Production
- **Monitoring**: Application Insights + Azure Monitor
- **Secrets**: Azure Key Vault

---

## 4. Adding a New Data Source

**4-Step Process**:

1. **Create Plugin Class**
```csharp
public class SharePointAdapter : IDocumentSource
{
    public string SourceType => "sharepoint";
    public SourceCapabilities Capabilities => new()
    {
        SupportsMcp = false,  // No MCP server
        SupportsRag = true    // Use Microsoft Graph API + RAG
    };
    // Implement interface methods
}
```

2. **Add to RagPlatform.Plugins Project**
```bash
# File: RagPlatform.Plugins/SharePointAdapter.cs
# That's it - auto-discovery handles registration
```

3. **Configure in appsettings.json**
```json
{
  "DataSources": {
    "SharePoint": {
      "Enabled": true,
      "TenantId": "xxx",
      "ClientId": "xxx",
      "ClientSecret": "xxx"
    }
  }
}
```

4. **Deploy**
```bash
dotnet build
dotnet publish
# Deploy to Azure App Service
```

**No application code changes needed** - the plugin system handles everything.

---

## 5. Migration Timeline

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| **Phase 1: Foundation** | 2 weeks | C# solution structure, `IDocumentSource` interface, Azure infrastructure (Terraform) |
| **Phase 2: Core Services** | 3 weeks | MCP client, RAG engine, vector store service, strategy selector |
| **Phase 3: OneNote Plugin** | 2 weeks | Port existing Python OneNote code to C# plugin |
| **Phase 4: API Layer** | 2 weeks | ASP.NET Core API, authentication, multi-tenancy |
| **Phase 5: Frontend Updates** | 2 weeks | Source selector UI, multi-source support |
| **Phase 6: Testing** | 3 weeks | Unit tests, integration tests, performance testing |
| **Phase 7: Production Features** | 3 weeks | Monitoring, audit logging, cost tracking |
| **Phase 8: Deployment** | 1 week | Production deployment, documentation |
| **TOTAL** | **18 weeks** | Production-ready multi-source RAG platform |

---

## 6. Key Design Decisions

### Why Plugin Architecture?
- **Loose Coupling**: Data sources are isolated, can be added/removed independently
- **Extensibility**: New sources require zero changes to core application
- **Testability**: Each plugin can be tested in isolation
- **Scalability**: Plugins can run in separate processes if needed

### Why Auto-Selection (MCP vs RAG)?
- **Performance**: Use fast MCP for simple queries (<500ms)
- **Intelligence**: Use RAG for complex semantic queries (2-10s)
- **Flexibility**: User can override auto-selection
- **Fallback**: Graceful degradation if preferred method unavailable

### Why C# .NET 8?
- **Enterprise-Grade**: Superior type safety, async/await, dependency injection
- **Azure Native**: First-class Azure SDK support
- **Performance**: 3-5x faster than Python for API workloads
- **Ecosystem**: Mature plugin frameworks, testing tools

### Why Azure?
- **PaaS Services**: Managed infrastructure reduces operational burden
- **Scalability**: Auto-scaling for API, Cosmos DB, AI Search
- **AI Integration**: Azure OpenAI Service with enterprise SLAs
- **Security**: Built-in Azure AD, Key Vault, Private Link support

---

## Summary

**How we're building**: Plugin architecture with `IDocumentSource` interface + automatic discovery

**Multiple sources/techniques**: Strategy selector auto-routes to MCP (fast) or RAG (intelligent) based on source capabilities and query complexity

**Technology**: C# .NET 8 backend, Azure PaaS services, React frontend, Terraform IaC, 18-week migration

**Result**: Plug-and-play multi-source RAG platform where adding a new data source requires only:
1. Create plugin class implementing `IDocumentSource`
2. Declare MCP/RAG capabilities
3. Deploy

No core application changes needed.