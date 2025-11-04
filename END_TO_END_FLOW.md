# End-to-End Flow: Adding a Data Source & Query Execution

## Scenario: Adding Confluence as a Data Source

Confluence has an MCP server available (`@modelcontextprotocol/server-confluence`) and we also want RAG support for semantic search.

---

## Part 1: Adding the Data Source

### Step 1: Create the Plugin Class

**File: `RagPlatform.Plugins/ConfluenceAdapter.cs`**

```csharp
using RagPlatform.Core;
using RagPlatform.Infrastructure.Mcp;
using Microsoft.Extensions.Logging;

namespace RagPlatform.Plugins;

public class ConfluenceAdapter : IDocumentSource
{
    private readonly IMcpClient _mcpClient;
    private readonly ILogger<ConfluenceAdapter> _logger;
    private SourceConfiguration? _config;
    private bool _isInitialized;

    public ConfluenceAdapter(
        IMcpClientFactory mcpClientFactory,
        ILogger<ConfluenceAdapter> logger)
    {
        _mcpClient = mcpClientFactory.CreateClient("confluence");
        _logger = logger;
    }

    // 1. Declare identity and capabilities
    public string SourceType => "confluence";
    public string DisplayName => "Confluence";

    public SourceCapabilities Capabilities => new()
    {
        SupportsMcp = true,              // Has MCP server
        SupportsRag = true,              // Can do semantic search
        SupportsRealtime = true,         // Real-time via MCP
        RequiresIndexing = true,         // Need to index for RAG
        SupportsMetadataFiltering = true,
        SupportedMimeTypes = new[] { "text/html", "text/plain" }
    };

    // 2. Initialize connection to MCP server
    public async Task<bool> InitializeAsync(
        SourceConfiguration config,
        CancellationToken ct = default)
    {
        _config = config;

        // Connect to MCP server via STDIO
        await _mcpClient.ConnectAsync(new McpServerConfig
        {
            Command = "node",
            Arguments = "node_modules/@modelcontextprotocol/server-confluence/dist/index.js",
            WorkingDirectory = config.McpServerPath,
            Environment = new Dictionary<string, string>
            {
                ["CONFLUENCE_URL"] = config.GetSetting("ConfluenceUrl"),
                ["CONFLUENCE_USERNAME"] = config.GetSetting("Username"),
                ["CONFLUENCE_API_TOKEN"] = config.GetSetting("ApiToken")
            }
        }, ct);

        _isInitialized = true;
        _logger.LogInformation("Confluence adapter initialized");
        return true;
    }

    // 3. Fetch all documents for RAG indexing
    public async Task<IEnumerable<SourceDocument>> GetAllDocumentsAsync(
        FetchOptions options,
        CancellationToken ct = default)
    {
        if (!_isInitialized)
            throw new InvalidOperationException("Adapter not initialized");

        var documents = new List<SourceDocument>();

        // Step 3a: Get all spaces via MCP
        var spacesResponse = await _mcpClient.SendRequestAsync(new McpRequest
        {
            Method = "tools/call",
            Params = new
            {
                name = "confluence_list_spaces"
            }
        }, ct);

        var spaces = spacesResponse.Result.Content.Select(c => c.Text).ToList();

        // Step 3b: For each space, get all pages
        foreach (var spaceKey in spaces)
        {
            var pagesResponse = await _mcpClient.SendRequestAsync(new McpRequest
            {
                Method = "tools/call",
                Params = new
                {
                    name = "confluence_get_space_pages",
                    arguments = new { spaceKey }
                }
            }, ct);

            // Step 3c: For each page, get full content
            foreach (var pageInfo in pagesResponse.Result.Content)
            {
                var pageId = pageInfo.PageId;

                var pageContentResponse = await _mcpClient.SendRequestAsync(new McpRequest
                {
                    Method = "tools/call",
                    Params = new
                    {
                        name = "confluence_get_page",
                        arguments = new { pageId }
                    }
                }, ct);

                var pageContent = pageContentResponse.Result.Content.First().Text;

                // Step 3d: Convert to SourceDocument
                documents.Add(new SourceDocument
                {
                    Id = $"confluence:{spaceKey}:{pageId}",
                    SourceType = SourceType,
                    Title = pageInfo.Title,
                    Content = pageContent,  // HTML content
                    Url = $"{_config.GetSetting("ConfluenceUrl")}/pages/{pageId}",
                    Metadata = new Dictionary<string, object>
                    {
                        ["spaceKey"] = spaceKey,
                        ["pageId"] = pageId,
                        ["author"] = pageInfo.Author,
                        ["lastModified"] = pageInfo.LastModified,
                        ["version"] = pageInfo.Version
                    },
                    FetchedAt = DateTime.UtcNow
                });
            }
        }

        _logger.LogInformation("Fetched {Count} Confluence pages", documents.Count);
        return documents;
    }

    // 4. Get a specific document (for real-time MCP queries)
    public async Task<SourceDocument?> GetDocumentAsync(
        string documentId,
        CancellationToken ct = default)
    {
        // Extract page ID from documentId (format: "confluence:SPACE:12345")
        var parts = documentId.Split(':');
        var pageId = parts[2];

        var response = await _mcpClient.SendRequestAsync(new McpRequest
        {
            Method = "tools/call",
            Params = new
            {
                name = "confluence_get_page",
                arguments = new { pageId }
            }
        }, ct);

        var content = response.Result.Content.First();

        return new SourceDocument
        {
            Id = documentId,
            SourceType = SourceType,
            Title = content.Title,
            Content = content.Text,
            Url = $"{_config.GetSetting("ConfluenceUrl")}/pages/{pageId}",
            FetchedAt = DateTime.UtcNow
        };
    }

    // 5. Execute MCP query directly (for simple lookups)
    public async Task<McpResponse> ExecuteMcpQueryAsync(
        McpRequest request,
        CancellationToken ct = default)
    {
        // Pass through to MCP server
        return await _mcpClient.SendRequestAsync(request, ct);
    }

    // 6. Health check
    public async Task<HealthStatus> CheckHealthAsync(CancellationToken ct = default)
    {
        try
        {
            var response = await _mcpClient.SendRequestAsync(new McpRequest
            {
                Method = "tools/list"
            }, ct);

            return new HealthStatus
            {
                IsHealthy = true,
                Message = "MCP server responding",
                ResponseTimeMs = response.ResponseTimeMs
            };
        }
        catch (Exception ex)
        {
            return new HealthStatus
            {
                IsHealthy = false,
                Message = ex.Message
            };
        }
    }
}
```

### Step 2: Register in Dependency Injection

**File: `RagPlatform.Api/Program.cs`**

```csharp
var builder = WebApplication.CreateBuilder(args);

// Auto-discover all plugins implementing IDocumentSource
builder.Services.DiscoverAndRegisterPlugins();

// Core services
builder.Services.AddScoped<IQueryEngine, QueryEngine>();
builder.Services.AddScoped<IStrategySelector, StrategySelector>();
builder.Services.AddScoped<IMcpStrategy, McpStrategy>();
builder.Services.AddScoped<IRagStrategy, RagStrategy>();

// Infrastructure
builder.Services.AddSingleton<IMcpClientFactory, McpClientFactory>();
builder.Services.AddScoped<IVectorStore, AzureAiSearchVectorStore>();
builder.Services.AddScoped<IEmbeddingService, AzureOpenAiEmbeddingService>();
builder.Services.AddScoped<ILlmService, AzureOpenAiLlmService>();

var app = builder.Build();
app.Run();
```

**Plugin Discovery Implementation:**

```csharp
public static class PluginRegistrationExtensions
{
    public static IServiceCollection DiscoverAndRegisterPlugins(
        this IServiceCollection services)
    {
        // Find all assemblies with "RagPlatform.Plugins" in the name
        var pluginAssemblies = AppDomain.CurrentDomain.GetAssemblies()
            .Where(a => a.GetName().Name?.StartsWith("RagPlatform.Plugins") ?? false)
            .ToList();

        foreach (var assembly in pluginAssemblies)
        {
            // Find all types implementing IDocumentSource
            var pluginTypes = assembly.GetTypes()
                .Where(t => typeof(IDocumentSource).IsAssignableFrom(t)
                         && !t.IsInterface
                         && !t.IsAbstract)
                .ToList();

            foreach (var pluginType in pluginTypes)
            {
                services.AddScoped(typeof(IDocumentSource), pluginType);
                Console.WriteLine($"Registered plugin: {pluginType.Name}");
            }
        }

        return services;
    }
}
```

### Step 3: Configure in appsettings.json

**File: `RagPlatform.Api/appsettings.json`**

```json
{
  "DataSources": {
    "Confluence": {
      "Enabled": true,
      "DisplayName": "Confluence",
      "McpServerPath": "./mcp-servers/confluence",
      "Settings": {
        "ConfluenceUrl": "https://your-company.atlassian.net/wiki",
        "Username": "user@company.com",
        "ApiToken": "your-api-token-from-keyvault"
      },
      "IndexingSchedule": "0 2 * * *",  // Daily at 2 AM
      "CacheConfig": {
        "Enabled": true,
        "TtlMinutes": 30
      }
    }
  }
}
```

### Step 4: Initial Data Indexing

When the plugin is first added, we need to index all Confluence pages into the vector store for RAG queries.

**File: `RagPlatform.Infrastructure/Indexing/IndexingService.cs`**

```csharp
public class IndexingService : BackgroundService
{
    private readonly IServiceProvider _serviceProvider;
    private readonly ILogger<IndexingService> _logger;

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        while (!stoppingToken.IsCancellationRequested)
        {
            using var scope = _serviceProvider.CreateScope();
            var sources = scope.ServiceProvider.GetServices<IDocumentSource>();
            var vectorStore = scope.ServiceProvider.GetRequiredService<IVectorStore>();
            var embeddingService = scope.ServiceProvider.GetRequiredService<IEmbeddingService>();

            foreach (var source in sources)
            {
                if (!source.Capabilities.SupportsRag)
                    continue; // Skip sources that don't need indexing

                _logger.LogInformation("Starting indexing for {Source}", source.SourceType);

                // Step 1: Fetch all documents from source
                var documents = await source.GetAllDocumentsAsync(new FetchOptions
                {
                    IncludeContent = true,
                    IncludeMetadata = true
                });

                // Step 2: Chunk large documents
                var chunks = new List<DocumentChunk>();
                foreach (var doc in documents)
                {
                    var docChunks = ChunkDocument(doc, maxTokens: 512);
                    chunks.AddRange(docChunks);
                }

                _logger.LogInformation("Created {Count} chunks from {DocCount} documents",
                    chunks.Count, documents.Count());

                // Step 3: Generate embeddings in batches
                var batchSize = 100;
                for (int i = 0; i < chunks.Count; i += batchSize)
                {
                    var batch = chunks.Skip(i).Take(batchSize).ToList();

                    var texts = batch.Select(c => c.Content).ToList();
                    var embeddings = await embeddingService.GenerateEmbeddingsAsync(texts);

                    // Step 4: Store in vector database
                    var vectorDocuments = batch.Zip(embeddings, (chunk, embedding) =>
                        new VectorDocument
                        {
                            Id = chunk.Id,
                            SourceDocumentId = chunk.SourceDocumentId,
                            SourceType = chunk.SourceType,
                            Content = chunk.Content,
                            Embedding = embedding,
                            Metadata = chunk.Metadata
                        });

                    await vectorStore.UpsertAsync(vectorDocuments);

                    _logger.LogInformation("Indexed batch {Current}/{Total}",
                        i + batch.Count, chunks.Count);
                }

                _logger.LogInformation("Indexing complete for {Source}", source.SourceType);
            }

            // Wait for next scheduled run
            await Task.Delay(TimeSpan.FromHours(24), stoppingToken);
        }
    }

    private List<DocumentChunk> ChunkDocument(SourceDocument doc, int maxTokens)
    {
        var chunks = new List<DocumentChunk>();
        var paragraphs = doc.Content.Split("\n\n");

        var currentChunk = new StringBuilder();
        var currentTokens = 0;
        var chunkIndex = 0;

        foreach (var paragraph in paragraphs)
        {
            var paragraphTokens = paragraph.Length / 4; // Rough estimate

            if (currentTokens + paragraphTokens > maxTokens && currentChunk.Length > 0)
            {
                // Save current chunk
                chunks.Add(new DocumentChunk
                {
                    Id = $"{doc.Id}:chunk:{chunkIndex}",
                    SourceDocumentId = doc.Id,
                    SourceType = doc.SourceType,
                    Content = currentChunk.ToString(),
                    ChunkIndex = chunkIndex,
                    Metadata = new Dictionary<string, object>(doc.Metadata)
                    {
                        ["title"] = doc.Title,
                        ["url"] = doc.Url,
                        ["chunkIndex"] = chunkIndex
                    }
                });

                currentChunk.Clear();
                currentTokens = 0;
                chunkIndex++;
            }

            currentChunk.Append(paragraph).Append("\n\n");
            currentTokens += paragraphTokens;
        }

        // Add final chunk
        if (currentChunk.Length > 0)
        {
            chunks.Add(new DocumentChunk
            {
                Id = $"{doc.Id}:chunk:{chunkIndex}",
                SourceDocumentId = doc.Id,
                SourceType = doc.SourceType,
                Content = currentChunk.ToString(),
                ChunkIndex = chunkIndex,
                Metadata = new Dictionary<string, object>(doc.Metadata)
                {
                    ["title"] = doc.Title,
                    ["url"] = doc.Url,
                    ["chunkIndex"] = chunkIndex
                }
            });
        }

        return chunks;
    }
}
```

---

## Part 2: Data Storage Architecture

### Storage Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    Data Storage Layers                       │
└─────────────────────────────────────────────────────────────┘

1. SOURCE SYSTEM (Confluence)
   └─> Original data lives here
       - Spaces, pages, attachments
       - Real-time access via MCP

2. DOCUMENT STORE (Azure Cosmos DB)
   └─> Metadata + small documents
       {
         "id": "confluence:ENG:12345",
         "sourceType": "confluence",
         "title": "API Design Guidelines",
         "url": "https://company.atlassian.net/wiki/pages/12345",
         "metadata": {
           "spaceKey": "ENG",
           "pageId": "12345",
           "author": "john.doe",
           "lastModified": "2025-01-15T10:30:00Z",
           "version": 5
         },
         "lastIndexed": "2025-01-15T02:00:00Z",
         "tenantId": "tenant-123"
       }

3. VECTOR STORE (Azure AI Search)
   └─> Embeddings + chunks for RAG
       {
         "id": "confluence:ENG:12345:chunk:0",
         "sourceDocumentId": "confluence:ENG:12345",
         "sourceType": "confluence",
         "content": "API Design Guidelines\n\nOur APIs follow REST principles...",
         "contentVector": [0.123, -0.456, 0.789, ...],  // 1536 dimensions
         "metadata": {
           "title": "API Design Guidelines",
           "url": "https://...",
           "spaceKey": "ENG",
           "chunkIndex": 0
         },
         "tenantId": "tenant-123"
       }

4. CACHE LAYER (Azure Redis Cache)
   └─> Hot query results
       Key: "query:hash:abc123"
       Value: {
         "query": "What are our API guidelines?",
         "result": "...",
         "sources": [...],
         "timestamp": "2025-01-15T15:45:00Z",
         "ttl": 1800  // 30 minutes
       }
```

### Data Flow: Indexing

```
┌──────────────┐
│  Confluence  │ (Source System)
│   MCP Server │
└──────┬───────┘
       │ 1. GetAllDocumentsAsync()
       │    via MCP calls
       ▼
┌──────────────────────┐
│ ConfluenceAdapter    │
│  - Fetches pages     │
│  - Converts to       │
│    SourceDocument[]  │
└──────┬───────────────┘
       │ 2. Documents returned
       ▼
┌──────────────────────┐
│  IndexingService     │
│  - Chunks documents  │
│  - 512 tokens/chunk  │
└──────┬───────────────┘
       │ 3. Document chunks
       ▼
┌──────────────────────┐
│  EmbeddingService    │
│  (Azure OpenAI)      │
│  - text-embedding-3  │
│  - 1536 dimensions   │
└──────┬───────────────┘
       │ 4. Embeddings (vectors)
       ▼
┌──────────────────────────────────┐
│  Azure AI Search (Vector Store)  │
│  - HNSW algorithm                │
│  - Stores chunks + embeddings    │
└──────────────────────────────────┘
       │ Also stores metadata in
       ▼
┌──────────────────────┐
│  Azure Cosmos DB     │
│  - Document metadata │
│  - Indexing status   │
└──────────────────────┘
```

---

## Part 3: Query Execution Flow

### User asks: "What are our API design guidelines?"

```
┌─────────────┐
│  React UI   │
└──────┬──────┘
       │ POST /api/query
       │ {
       │   "query": "What are our API design guidelines?",
       │   "sources": ["confluence"],
       │   "preferredMode": null  // Auto-select
       │ }
       ▼
┌───────────────────────────────────────────────────────────┐
│  QueryController (ASP.NET Core)                           │
└──────┬────────────────────────────────────────────────────┘
       │
       ▼
┌───────────────────────────────────────────────────────────┐
│  Step 1: Cache Check                                      │
│  ──────────────────────────────────────────────────────   │
│  QueryHash = SHA256("What are our API design guidelines?")│
│  CacheKey = "query:hash:{hash}:source:confluence"         │
│                                                            │
│  Redis.Get(CacheKey)                                      │
│    └─> MISS (not cached)                                  │
└──────┬────────────────────────────────────────────────────┘
       │
       ▼
┌───────────────────────────────────────────────────────────┐
│  Step 2: Load Data Source Plugin                         │
│  ──────────────────────────────────────────────────────   │
│  var source = _sources.First(s =>                         │
│      s.SourceType == "confluence");                       │
│                                                            │
│  // Returns: ConfluenceAdapter instance                   │
│  // Capabilities: { SupportsMcp: true, SupportsRag: true }│
└──────┬────────────────────────────────────────────────────┘
       │
       ▼
┌───────────────────────────────────────────────────────────┐
│  Step 3: Strategy Selection                               │
│  ──────────────────────────────────────────────────────   │
│  _strategySelector.SelectStrategy(request, source)        │
│                                                            │
│  Analysis:                                                 │
│  - Query: "What are our API design guidelines?"          │
│  - Contains: "What are" (question word)                   │
│  - No simple lookup keywords ("get", "show", "find")      │
│  - Requires semantic understanding                        │
│  - Source supports both MCP and RAG                       │
│                                                            │
│  Decision: USE RAG (semantic search needed)               │
└──────┬────────────────────────────────────────────────────┘
       │
       ▼
┌───────────────────────────────────────────────────────────┐
│  Step 4: RAG Strategy Execution                           │
│  ──────────────────────────────────────────────────────   │
│  _ragStrategy.ExecuteAsync(request, source)               │
└──────┬────────────────────────────────────────────────────┘
       │
       ▼
```

### RAG Strategy Deep Dive

```csharp
public class RagStrategy : IQueryStrategy
{
    private readonly IVectorStore _vectorStore;
    private readonly IEmbeddingService _embeddingService;
    private readonly ILlmService _llmService;
    private readonly IRagTechniqueSelector _techniqueSelector;

    public async Task<QueryResult> ExecuteAsync(
        QueryRequest request,
        IDocumentSource source,
        CancellationToken ct = default)
    {
        // ─────────────────────────────────────────────────────────
        // STEP 4A: Select RAG Technique
        // ─────────────────────────────────────────────────────────
        var technique = _techniqueSelector.SelectTechnique(request);
        // Result: "RAG-Fusion" (combines multiple query variations)

        // ─────────────────────────────────────────────────────────
        // STEP 4B: Generate Query Variations (Multi-Query)
        // ─────────────────────────────────────────────────────────
        var variations = await GenerateQueryVariations(request.Query);

        // Original: "What are our API design guidelines?"
        // Variations:
        // 1. "API design best practices"
        // 2. "REST API guidelines and standards"
        // 3. "API documentation requirements"

        // ─────────────────────────────────────────────────────────
        // STEP 4C: Generate Embeddings for Each Variation
        // ─────────────────────────────────────────────────────────
        var queryEmbeddings = await _embeddingService.GenerateEmbeddingsAsync(
            variations);

        // Each variation becomes a 1536-dimensional vector

        // ─────────────────────────────────────────────────────────
        // STEP 4D: Vector Search (Parallel)
        // ─────────────────────────────────────────────────────────
        var searchTasks = queryEmbeddings.Select(embedding =>
            _vectorStore.SearchAsync(new VectorSearchRequest
            {
                Vector = embedding,
                TopK = 10,
                Filters = new Dictionary<string, object>
                {
                    ["sourceType"] = source.SourceType,
                    ["tenantId"] = request.TenantId
                }
            }, ct)
        );

        var searchResults = await Task.WhenAll(searchTasks);

        // Each search returns 10 chunks, total: 30 chunks

        // ─────────────────────────────────────────────────────────
        // STEP 4E: Reciprocal Rank Fusion (RRF)
        // ─────────────────────────────────────────────────────────
        var fusedResults = ApplyReciprocalRankFusion(searchResults);

        /*
        RRF Formula: score = Σ(1 / (k + rank))
        where k = 60 (constant)

        Document "confluence:ENG:12345:chunk:0" appears in:
        - Query 1 results at rank 1: 1/(60+1) = 0.0164
        - Query 2 results at rank 3: 1/(60+3) = 0.0159
        - Query 3 results at rank 2: 1/(60+2) = 0.0161
        Total RRF score: 0.0484

        Top 10 documents after fusion ranked by RRF score
        */

        // ─────────────────────────────────────────────────────────
        // STEP 4F: Re-ranking with Cohere
        // ─────────────────────────────────────────────────────────
        var rerankedResults = await ReRankResults(
            request.Query,
            fusedResults.Take(20).ToList() // Re-rank top 20
        );

        // Cohere re-ranker scores documents by relevance to original query
        // Returns top 5 most relevant chunks

        // ─────────────────────────────────────────────────────────
        // STEP 4G: Build Context for LLM
        // ─────────────────────────────────────────────────────────
        var context = BuildContext(rerankedResults.Take(5));

        /*
        Context:

        [Document 1: API Design Guidelines, chunk 0]
        Our APIs follow REST principles. All endpoints must:
        1. Use proper HTTP methods (GET, POST, PUT, DELETE)
        2. Return appropriate status codes
        3. Use JSON for request/response bodies
        ...

        [Document 2: API Design Guidelines, chunk 1]
        Versioning: All APIs must include a version in the URL path.
        Example: /api/v1/users
        Breaking changes require a new version number.
        ...

        [Document 3: API Standards, chunk 0]
        Authentication: All APIs must use OAuth 2.0 with JWT tokens.
        Include the Authorization header: Bearer {token}
        ...
        */

        // ─────────────────────────────────────────────────────────
        // STEP 4H: Generate Answer with LLM (GPT-4)
        // ─────────────────────────────────────────────────────────
        var systemPrompt = @"You are a helpful assistant that answers questions
based on the provided context. Always cite your sources using [Doc N] notation.";

        var userPrompt = $@"
Context:
{context}

Question: {request.Query}

Provide a comprehensive answer based on the context above.
Include citations to specific documents.";

        var llmResponse = await _llmService.GenerateCompletionAsync(
            new LlmRequest
            {
                SystemPrompt = systemPrompt,
                UserPrompt = userPrompt,
                Temperature = 0.3,  // Low temperature for factual answers
                MaxTokens = 1000
            }, ct);

        /*
        LLM Response:

        "Our API design guidelines are based on REST principles [Doc 1].

        Key requirements include:

        1. **HTTP Methods**: Use proper HTTP methods - GET for retrieval,
           POST for creation, PUT for updates, and DELETE for removal [Doc 1]

        2. **Versioning**: All APIs must include version in the URL path
           (e.g., /api/v1/users). Breaking changes require a new version [Doc 2]

        3. **Authentication**: All APIs must use OAuth 2.0 with JWT tokens.
           Include the Authorization header with Bearer token [Doc 3]

        4. **Response Format**: Use JSON for all request and response bodies
           with appropriate HTTP status codes [Doc 1]

        These guidelines ensure consistency and maintainability across all
        our API endpoints."
        */

        // ─────────────────────────────────────────────────────────
        // STEP 4I: Build Final Result
        // ─────────────────────────────────────────────────────────
        var result = new QueryResult
        {
            Answer = llmResponse.Content,
            Sources = rerankedResults.Select(r => new SourceReference
            {
                DocumentId = r.SourceDocumentId,
                Title = r.Metadata["title"].ToString(),
                Url = r.Metadata["url"].ToString(),
                Excerpt = r.Content.Substring(0, 200),
                Score = r.Score
            }).ToList(),
            Strategy = QueryMode.Rag,
            TotalTimeMs = stopwatch.ElapsedMilliseconds,
            Metadata = new Dictionary<string, object>
            {
                ["ragTechnique"] = "RAG-Fusion",
                ["queryVariations"] = variations.Count,
                ["chunksRetrieved"] = searchResults.Sum(r => r.Count()),
                ["rerankedChunks"] = rerankedResults.Count,
                ["llmTokensUsed"] = llmResponse.TokensUsed
            }
        };

        // ─────────────────────────────────────────────────────────
        // STEP 4J: Cache Result
        // ─────────────────────────────────────────────────────────
        await _cache.SetAsync(
            key: $"query:hash:{queryHash}:source:{source.SourceType}",
            value: result,
            expiration: TimeSpan.FromMinutes(30)
        );

        return result;
    }
}
```

### Complete Flow Diagram

```
USER QUERY: "What are our API design guidelines?"
│
├─> [Cache Check] ──> MISS
│
├─> [Load Plugin] ──> ConfluenceAdapter
│                      { SupportsMcp: true, SupportsRag: true }
│
├─> [Strategy Selection] ──> RAG (semantic search needed)
│
└─> [RAG Execution]
    │
    ├─> 1. Generate Query Variations (Multi-Query)
    │   ├─ "API design best practices"
    │   ├─ "REST API guidelines and standards"
    │   └─ "API documentation requirements"
    │
    ├─> 2. Generate Embeddings (Azure OpenAI)
    │   └─ 3 vectors × 1536 dimensions each
    │
    ├─> 3. Vector Search (Azure AI Search)
    │   ├─ Query 1 ──> 10 chunks
    │   ├─ Query 2 ──> 10 chunks
    │   └─ Query 3 ──> 10 chunks
    │   Total: 30 chunks retrieved
    │
    ├─> 4. Reciprocal Rank Fusion
    │   └─ Combine rankings ──> Top 20 unique chunks
    │
    ├─> 5. Re-ranking (Cohere)
    │   └─ Score by relevance ──> Top 5 chunks
    │
    ├─> 6. Build Context
    │   └─ Concatenate top 5 chunks with metadata
    │
    ├─> 7. LLM Generation (GPT-4)
    │   ├─ System Prompt: "Answer based on context"
    │   ├─ User Prompt: Context + Question
    │   └─ Temperature: 0.3 (factual)
    │
    ├─> 8. Format Result
    │   ├─ Answer text
    │   ├─ Source citations [Doc 1], [Doc 2], [Doc 3]
    │   ├─ Source references (title, URL, excerpt)
    │   └─ Metadata (technique, timing, tokens)
    │
    └─> 9. Cache Result (30 min TTL)

RESPONSE (2-10 seconds total):
{
  "answer": "Our API design guidelines are based on REST principles...",
  "sources": [
    {
      "title": "API Design Guidelines",
      "url": "https://company.atlassian.net/wiki/pages/12345",
      "excerpt": "Our APIs follow REST principles..."
    }
  ],
  "strategy": "rag",
  "totalTimeMs": 3847
}
```

---

## Alternative Flow: Simple MCP Query

### User asks: "Show me the API Design Guidelines page"

```
USER QUERY: "Show me the API Design Guidelines page"
│
├─> [Cache Check] ──> MISS
│
├─> [Load Plugin] ──> ConfluenceAdapter
│
├─> [Strategy Selection]
│   Analysis:
│   - Contains "Show me" (simple lookup keyword)
│   - Specific page requested
│   - No semantic analysis needed
│   Decision: USE MCP (fast, direct)
│
└─> [MCP Execution]
    │
    ├─> 1. Parse Intent
    │   └─ Action: "get_page"
    │       Query: "API Design Guidelines"
    │
    ├─> 2. Build MCP Request
    │   {
    │     "method": "tools/call",
    │     "params": {
    │       "name": "confluence_search_pages",
    │       "arguments": {
    │         "query": "API Design Guidelines",
    │         "limit": 1
    │       }
    │     }
    │   }
    │
    ├─> 3. Send to MCP Server (STDIO)
    │   ConfluenceAdapter._mcpClient.SendRequestAsync()
    │   │
    │   └─> Process: node server-confluence/index.js
    │       │
    │       ├─> MCP Server receives JSON-RPC via stdin
    │       ├─> Calls Confluence REST API
    │       ├─> Returns result via stdout
    │       └─> Response time: ~200ms
    │
    ├─> 4. Parse MCP Response
    │   {
    │     "result": {
    │       "content": [
    │         {
    │           "type": "text",
    │           "text": "API Design Guidelines\n\nOur APIs follow REST...",
    │           "pageId": "12345",
    │           "url": "https://company.atlassian.net/wiki/pages/12345"
    │         }
    │       ]
    │     }
    │   }
    │
    ├─> 5. Format Result
    │   {
    │     "answer": "Here is the API Design Guidelines page:\n\n[content]",
    │     "sources": [
    │       {
    │         "title": "API Design Guidelines",
    │         "url": "https://...",
    │         "pageId": "12345"
    │       }
    │     ],
    │     "strategy": "mcp",
    │     "totalTimeMs": 287
    │   }
    │
    └─> 6. Cache Result

RESPONSE (<500ms total) - Much faster than RAG!
```

---

## Performance Comparison

| Metric | MCP Query | RAG Query |
|--------|-----------|-----------|
| **Total Time** | 200-500ms | 2-10 seconds |
| **Steps** | 3 (parse → MCP call → format) | 9 (variations → embeddings → search → fusion → rerank → LLM → format) |
| **External Calls** | 1 (MCP server) | 5-10 (embeddings API, vector search, reranker, LLM) |
| **Token Usage** | 0 | ~2,000-4,000 tokens |
| **Cost per Query** | ~$0 | ~$0.02-0.08 |
| **Use Case** | Direct lookups, specific documents | Semantic search, complex questions, summarization |
| **Freshness** | Real-time (always current) | Depends on indexing schedule (may be stale) |

---

## Summary

### Adding a Data Source (Confluence)

1. **Create plugin class** implementing `IDocumentSource`
2. **Declare capabilities** (MCP: yes, RAG: yes)
3. **Implement methods**:
   - `GetAllDocumentsAsync()` - Fetch all docs for indexing
   - `ExecuteMcpQueryAsync()` - Direct MCP passthrough
4. **Auto-discovery** registers plugin at startup
5. **Background indexing** chunks documents, generates embeddings, stores in vector DB

### Data Storage

- **Source System**: Original data (Confluence)
- **Cosmos DB**: Document metadata, indexing status
- **Azure AI Search**: Vector embeddings (1536-dim) + chunks
- **Redis Cache**: Hot query results (30 min TTL)

### Query Execution

**MCP Path** (Simple queries):
- Parse → MCP call → Format → Return (200-500ms)

**RAG Path** (Complex queries):
- Generate variations → Embed → Vector search → Fusion → Re-rank → LLM → Format → Return (2-10s)

**Auto-Selection** chooses the optimal path based on query intent and source capabilities.