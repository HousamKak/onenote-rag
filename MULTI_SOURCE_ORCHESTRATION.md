# Multi-Source Query Orchestration

## Problem Statement

With multiple data sources (Confluence, OneNote, SQL Database, SharePoint, etc.), we need:

1. **Source Selection**: Determine which data sources are relevant to the query
2. **Parallel Search**: Search selected sources concurrently
3. **Result Fusion**: Combine results from multiple sources
4. **Source Isolation**: Keep each source in separate vector index

## Architecture Overview

```
User Query: "What are our API guidelines?"
    ↓
┌─────────────────────────────────────────────────────────┐
│ Step 1: Source Selection (Route to relevant sources)   │
└─────────────────────────────────────────────────────────┘
    ↓
Selected: [Confluence, SharePoint]  (not OneNote, SQL DB)
    ↓
┌─────────────────────────────────────────────────────────┐
│ Step 2: Parallel Vector Search (Only selected sources) │
└─────────────────────────────────────────────────────────┘
    ↓
Confluence Results: 10 chunks + SharePoint Results: 10 chunks
    ↓
┌─────────────────────────────────────────────────────────┐
│ Step 3: Cross-Source Fusion & Re-ranking               │
└─────────────────────────────────────────────────────────┘
    ↓
Top 5 chunks (mixed from both sources)
    ↓
┌─────────────────────────────────────────────────────────┐
│ Step 4: LLM Generation with Multi-Source Context       │
└─────────────────────────────────────────────────────────┘
    ↓
Answer with citations from multiple sources
```

---

## Part 1: Storage Architecture - Separate Vector Indexes

### Azure AI Search - Multiple Indexes

Each data source gets its own vector index:

```
Azure AI Search Service
├── Index: "confluence-vectors"
│   ├── Documents: 15,000 chunks
│   └── Schema:
│       - id: string
│       - sourceDocumentId: string
│       - content: string
│       - contentVector: Collection(Single) [1536 dimensions]
│       - tenantId: string
│       - metadata: Complex
│
├── Index: "onenote-vectors"
│   ├── Documents: 8,000 chunks
│   └── Same schema
│
├── Index: "sharepoint-vectors"
│   ├── Documents: 12,000 chunks
│   └── Same schema
│
├── Index: "sqldatabase-vectors"
│   ├── Documents: 5,000 chunks (schema representations)
│   └── Same schema
│
└── Index: "notion-vectors"
    ├── Documents: 6,000 chunks
    └── Same schema
```

**Why Separate Indexes?**

✅ **Isolation**: Each source can be reindexed independently
✅ **Performance**: Smaller indexes = faster searches
✅ **Management**: Can delete/rebuild one source without affecting others
✅ **Security**: Can apply different access controls per source
✅ **Cost Optimization**: Can use different index tiers per source

### Implementation

```csharp
public interface IVectorStore
{
    Task<IEnumerable<SearchResult>> SearchAsync(
        string indexName,           // Which index to search
        VectorSearchRequest request,
        CancellationToken ct = default);

    Task UpsertAsync(
        string indexName,
        IEnumerable<VectorDocument> documents,
        CancellationToken ct = default);
}

public class AzureAiSearchVectorStore : IVectorStore
{
    private readonly SearchIndexClient _indexClient;
    private readonly Dictionary<string, SearchClient> _searchClients;

    public AzureAiSearchVectorStore(IConfiguration config)
    {
        var endpoint = config["AzureSearch:Endpoint"];
        var credential = new AzureKeyCredential(config["AzureSearch:ApiKey"]);

        _indexClient = new SearchIndexClient(new Uri(endpoint), credential);
        _searchClients = new Dictionary<string, SearchClient>();
    }

    private SearchClient GetSearchClient(string indexName)
    {
        if (!_searchClients.ContainsKey(indexName))
        {
            _searchClients[indexName] = _indexClient.GetSearchClient(indexName);
        }
        return _searchClients[indexName];
    }

    public async Task<IEnumerable<SearchResult>> SearchAsync(
        string indexName,
        VectorSearchRequest request,
        CancellationToken ct = default)
    {
        var searchClient = GetSearchClient(indexName);

        var searchOptions = new SearchOptions
        {
            VectorSearch = new()
            {
                Queries = { new VectorizedQuery(request.Vector.ToArray())
                {
                    KNearestNeighborsCount = request.TopK,
                    Fields = { "contentVector" }
                }}
            },
            Size = request.TopK,
            Filter = BuildFilter(request.Filters)
        };

        var response = await searchClient.SearchAsync<VectorDocument>(
            searchText: null,
            searchOptions,
            ct);

        var results = new List<SearchResult>();
        await foreach (var result in response.Value.GetResultsAsync())
        {
            results.Add(new SearchResult
            {
                Document = result.Document,
                Score = result.Score ?? 0,
                IndexName = indexName
            });
        }

        return results;
    }
}
```

---

## Part 2: Source Selection - Routing Intelligence

### Approach 1: Metadata-Based Routing (Simple)

```csharp
public class MetadataSourceSelector : ISourceSelector
{
    private readonly IEnumerable<IDocumentSource> _sources;

    public async Task<IEnumerable<IDocumentSource>> SelectSourcesAsync(
        QueryRequest request,
        CancellationToken ct = default)
    {
        var selectedSources = new List<IDocumentSource>();

        // 1. User explicitly specified sources
        if (request.SourceTypes?.Any() == true)
        {
            return _sources.Where(s => request.SourceTypes.Contains(s.SourceType));
        }

        // 2. Keyword-based routing
        var query = request.Query.ToLower();

        // Technical documentation → Confluence
        if (ContainsKeywords(query, "api", "guideline", "documentation", "standard"))
        {
            selectedSources.Add(_sources.First(s => s.SourceType == "confluence"));
        }

        // Meeting notes → OneNote
        if (ContainsKeywords(query, "meeting", "notes", "discussion", "decision"))
        {
            selectedSources.Add(_sources.First(s => s.SourceType == "onenote"));
        }

        // Database queries → SQL Database
        if (ContainsKeywords(query, "customer", "order", "product", "sales", "data"))
        {
            selectedSources.Add(_sources.First(s => s.SourceType == "sql-database"));
        }

        // Files and documents → SharePoint
        if (ContainsKeywords(query, "file", "document", "contract", "report"))
        {
            selectedSources.Add(_sources.First(s => s.SourceType == "sharepoint"));
        }

        // If no keywords matched, search all sources
        if (!selectedSources.Any())
        {
            return _sources;
        }

        return selectedSources;
    }

    private bool ContainsKeywords(string query, params string[] keywords)
    {
        return keywords.Any(keyword => query.Contains(keyword));
    }
}
```

**Limitations:**
- ❌ Relies on predefined keywords
- ❌ Doesn't understand context
- ✅ Fast and cheap

### Approach 2: LLM-Based Routing (Intelligent)

```csharp
public class LlmSourceSelector : ISourceSelector
{
    private readonly ILlmService _llmService;
    private readonly IEnumerable<IDocumentSource> _sources;

    public async Task<IEnumerable<IDocumentSource>> SelectSourcesAsync(
        QueryRequest request,
        CancellationToken ct = default)
    {
        // 1. User explicitly specified sources
        if (request.SourceTypes?.Any() == true)
        {
            return _sources.Where(s => request.SourceTypes.Contains(s.SourceType));
        }

        // 2. Build source descriptions
        var sourceDescriptions = _sources.Select(s => new
        {
            sourceType = s.SourceType,
            displayName = s.DisplayName,
            description = GetSourceDescription(s)
        }).ToList();

        var systemPrompt = $@"You are a routing assistant. Given a user query and available data sources,
determine which data sources are most likely to contain relevant information.

Available data sources:
{JsonSerializer.Serialize(sourceDescriptions, new JsonSerializerOptions { WriteIndented = true })}

Respond ONLY with a JSON array of source types, ordered by relevance (most relevant first).
Include 1-3 sources maximum. If uncertain, include multiple sources.

Examples:
Query: ""What are our API guidelines?""
Response: [""confluence"", ""sharepoint""]

Query: ""What did we discuss in last week's meeting?""
Response: [""onenote""]

Query: ""How many customers do we have in California?""
Response: [""sql-database""]

Query: ""Find the Q4 sales report""
Response: [""sharepoint"", ""confluence""]";

        var userPrompt = $"Query: {request.Query}";

        var llmResponse = await _llmService.GenerateCompletionAsync(new LlmRequest
        {
            SystemPrompt = systemPrompt,
            UserPrompt = userPrompt,
            Temperature = 0.1,
            MaxTokens = 100,
            ResponseFormat = "json"
        }, ct);

        // Parse LLM response
        var selectedSourceTypes = JsonSerializer.Deserialize<List<string>>(
            llmResponse.Content);

        // Return sources in order of relevance
        var orderedSources = new List<IDocumentSource>();
        foreach (var sourceType in selectedSourceTypes)
        {
            var source = _sources.FirstOrDefault(s => s.SourceType == sourceType);
            if (source != null)
            {
                orderedSources.Add(source);
            }
        }

        return orderedSources;
    }

    private string GetSourceDescription(IDocumentSource source)
    {
        return source.SourceType switch
        {
            "confluence" => "Technical documentation, API guidelines, architecture docs, team wikis",
            "onenote" => "Meeting notes, personal notes, project discussions, decisions",
            "sharepoint" => "Files, documents, contracts, reports, presentations",
            "sql-database" => "Structured data, customer records, orders, products, sales data",
            "notion" => "Project management, tasks, team collaboration, knowledge base",
            _ => "General documents and information"
        };
    }
}
```

### Approach 3: Hybrid Routing (Best of Both)

```csharp
public class HybridSourceSelector : ISourceSelector
{
    private readonly ILlmService _llmService;
    private readonly IEmbeddingService _embeddingService;
    private readonly IVectorStore _vectorStore;
    private readonly IEnumerable<IDocumentSource> _sources;

    // This approach uses a small "meta-index" with source descriptions
    private const string META_INDEX = "source-metadata";

    public async Task<IEnumerable<IDocumentSource>> SelectSourcesAsync(
        QueryRequest request,
        CancellationToken ct = default)
    {
        // 1. Generate embedding for the query
        var queryEmbedding = await _embeddingService.GenerateEmbeddingAsync(
            request.Query, ct);

        // 2. Search meta-index for relevant sources
        var metaResults = await _vectorStore.SearchAsync(META_INDEX, new VectorSearchRequest
        {
            Vector = queryEmbedding,
            TopK = 3,  // Top 3 most relevant sources
            Filters = new Dictionary<string, object>
            {
                ["tenantId"] = request.TenantId
            }
        }, ct);

        // 3. Extract source types from results
        var selectedSourceTypes = metaResults
            .Select(r => r.Document.Metadata["sourceType"].ToString())
            .Distinct()
            .ToList();

        // 4. Return corresponding source instances
        return _sources.Where(s => selectedSourceTypes.Contains(s.SourceType));
    }

    // Initialize meta-index (run once at startup)
    public async Task InitializeMetaIndexAsync()
    {
        var metaDocuments = new List<VectorDocument>();

        foreach (var source in _sources)
        {
            // Get sample documents from each source
            var sampleDocs = await GetSampleDocuments(source);

            // Create representative text for the source
            var representativeText = $@"
Source: {source.DisplayName}
Type: {source.SourceType}
Description: {GetSourceDescription(source)}

Sample content:
{string.Join("\n\n", sampleDocs.Select(d => d.Title + "\n" + d.Content.Substring(0, Math.Min(500, d.Content.Length))))}";

            // Generate embedding
            var embedding = await _embeddingService.GenerateEmbeddingAsync(representativeText);

            metaDocuments.Add(new VectorDocument
            {
                Id = $"meta:{source.SourceType}",
                Content = representativeText,
                Embedding = embedding,
                Metadata = new Dictionary<string, object>
                {
                    ["sourceType"] = source.SourceType,
                    ["displayName"] = source.DisplayName
                }
            });
        }

        await _vectorStore.UpsertAsync(META_INDEX, metaDocuments);
    }
}
```

---

## Part 3: Complete Query Orchestration Flow

### The Query Engine

```csharp
public class MultiSourceQueryEngine : IQueryEngine
{
    private readonly ISourceSelector _sourceSelector;
    private readonly IStrategySelector _strategySelector;
    private readonly IVectorStore _vectorStore;
    private readonly IEmbeddingService _embeddingService;
    private readonly ILlmService _llmService;
    private readonly ILogger<MultiSourceQueryEngine> _logger;

    public async Task<QueryResult> ExecuteAsync(
        QueryRequest request,
        CancellationToken ct = default)
    {
        var stopwatch = Stopwatch.StartNew();

        // ═══════════════════════════════════════════════════════
        // STEP 1: SOURCE SELECTION
        // ═══════════════════════════════════════════════════════
        _logger.LogInformation("Selecting sources for query: {Query}", request.Query);

        var selectedSources = await _sourceSelector.SelectSourcesAsync(request, ct);

        _logger.LogInformation("Selected {Count} sources: {Sources}",
            selectedSources.Count(),
            string.Join(", ", selectedSources.Select(s => s.SourceType)));

        // If no sources selected, return error
        if (!selectedSources.Any())
        {
            return new QueryResult
            {
                Answer = "No relevant data sources found for your query.",
                Strategy = QueryMode.None,
                TotalTimeMs = stopwatch.ElapsedMilliseconds
            };
        }

        // ═══════════════════════════════════════════════════════
        // STEP 2: STRATEGY SELECTION (per source)
        // ═══════════════════════════════════════════════════════
        var sourceStrategies = new Dictionary<IDocumentSource, IQueryStrategy>();

        foreach (var source in selectedSources)
        {
            var strategy = _strategySelector.SelectStrategy(request, source);
            sourceStrategies[source] = strategy;
        }

        // Check if all sources can use MCP (simple lookup)
        var allMcp = sourceStrategies.Values.All(s => s.Mode == QueryMode.Mcp);

        if (allMcp)
        {
            // ─────────────────────────────────────────────────
            // PATH A: ALL MCP (Simple lookup across sources)
            // ─────────────────────────────────────────────────
            return await ExecuteMcpQueryAcrossSourcesAsync(
                request, sourceStrategies, ct);
        }
        else
        {
            // ─────────────────────────────────────────────────
            // PATH B: RAG (Semantic search across sources)
            // ─────────────────────────────────────────────────
            return await ExecuteRagQueryAcrossSourcesAsync(
                request, selectedSources, stopwatch, ct);
        }
    }

    // ═══════════════════════════════════════════════════════
    // PATH B: Multi-Source RAG Query
    // ═══════════════════════════════════════════════════════
    private async Task<QueryResult> ExecuteRagQueryAcrossSourcesAsync(
        QueryRequest request,
        IEnumerable<IDocumentSource> sources,
        Stopwatch stopwatch,
        CancellationToken ct)
    {
        _logger.LogInformation("Executing RAG query across {Count} sources",
            sources.Count());

        // ─────────────────────────────────────────────────────
        // STEP 3A: Generate Query Embeddings
        // ─────────────────────────────────────────────────────
        var queryVariations = await GenerateQueryVariations(request.Query, ct);
        var queryEmbeddings = await _embeddingService.GenerateEmbeddingsAsync(
            queryVariations, ct);

        // ─────────────────────────────────────────────────────
        // STEP 3B: Parallel Vector Search Across All Sources
        // ─────────────────────────────────────────────────────
        var searchTasks = new List<Task<SourceSearchResult>>();

        foreach (var source in sources)
        {
            var indexName = GetIndexName(source);

            // For each source, search with all query variations
            var task = SearchSourceAsync(
                indexName,
                source,
                queryEmbeddings,
                request,
                ct);

            searchTasks.Add(task);
        }

        var sourceResults = await Task.WhenAll(searchTasks);

        _logger.LogInformation(
            "Retrieved {TotalChunks} total chunks from {SourceCount} sources",
            sourceResults.Sum(r => r.Results.Count),
            sourceResults.Length);

        // ─────────────────────────────────────────────────────
        // STEP 3C: Cross-Source Fusion
        // ─────────────────────────────────────────────────────
        var fusedResults = ApplyCrossSourceFusion(sourceResults);

        // ─────────────────────────────────────────────────────
        // STEP 3D: Re-ranking
        // ─────────────────────────────────────────────────────
        var rerankedResults = await ReRankResultsAsync(
            request.Query,
            fusedResults.Take(20).ToList(),
            ct);

        // ─────────────────────────────────────────────────────
        // STEP 3E: Build Multi-Source Context
        // ─────────────────────────────────────────────────────
        var context = BuildMultiSourceContext(rerankedResults.Take(5));

        // ─────────────────────────────────────────────────────
        // STEP 3F: LLM Generation
        // ─────────────────────────────────────────────────────
        var systemPrompt = @"You are a helpful assistant that answers questions
based on information from multiple data sources. Always cite which source
each piece of information came from using [Source: SourceName] notation.";

        var userPrompt = $@"
Context from multiple sources:
{context}

Question: {request.Query}

Provide a comprehensive answer. Include citations showing which source
each piece of information came from.";

        var llmResponse = await _llmService.GenerateCompletionAsync(
            new LlmRequest
            {
                SystemPrompt = systemPrompt,
                UserPrompt = userPrompt,
                Temperature = 0.3,
                MaxTokens = 1000
            }, ct);

        // ─────────────────────────────────────────────────────
        // STEP 3G: Build Result
        // ─────────────────────────────────────────────────────
        return new QueryResult
        {
            Answer = llmResponse.Content,
            Sources = rerankedResults.Select(r => new SourceReference
            {
                SourceType = r.SourceType,
                SourceDisplayName = r.SourceDisplayName,
                DocumentId = r.SourceDocumentId,
                Title = r.Metadata["title"].ToString(),
                Url = r.Metadata.ContainsKey("url")
                    ? r.Metadata["url"].ToString()
                    : null,
                Excerpt = r.Content.Substring(0, Math.Min(200, r.Content.Length)),
                Score = r.Score
            }).ToList(),
            Strategy = QueryMode.Rag,
            TotalTimeMs = stopwatch.ElapsedMilliseconds,
            Metadata = new Dictionary<string, object>
            {
                ["sourcesSearched"] = sources.Select(s => s.SourceType).ToList(),
                ["totalChunksRetrieved"] = sourceResults.Sum(r => r.Results.Count),
                ["rerankedChunks"] = rerankedResults.Count,
                ["llmTokensUsed"] = llmResponse.TokensUsed
            }
        };
    }

    // Helper: Search a single source with all query variations
    private async Task<SourceSearchResult> SearchSourceAsync(
        string indexName,
        IDocumentSource source,
        List<float[]> queryEmbeddings,
        QueryRequest request,
        CancellationToken ct)
    {
        var allResults = new List<SearchResult>();

        // Search with each query variation
        foreach (var embedding in queryEmbeddings)
        {
            var results = await _vectorStore.SearchAsync(indexName, new VectorSearchRequest
            {
                Vector = embedding,
                TopK = 10,
                Filters = new Dictionary<string, object>
                {
                    ["tenantId"] = request.TenantId
                }
            }, ct);

            allResults.AddRange(results);
        }

        return new SourceSearchResult
        {
            Source = source,
            Results = allResults
        };
    }

    // Helper: Get index name for a source
    private string GetIndexName(IDocumentSource source)
    {
        return $"{source.SourceType}-vectors";
    }

    // Helper: Apply cross-source fusion
    private List<SearchResult> ApplyCrossSourceFusion(
        IEnumerable<SourceSearchResult> sourceResults)
    {
        // Collect all results from all sources
        var allResults = sourceResults.SelectMany(sr => sr.Results).ToList();

        // Apply Reciprocal Rank Fusion across sources
        var fusionScores = new Dictionary<string, double>();

        foreach (var sourceResult in sourceResults)
        {
            var rankedResults = sourceResult.Results
                .OrderByDescending(r => r.Score)
                .ToList();

            for (int i = 0; i < rankedResults.Count; i++)
            {
                var docId = rankedResults[i].Document.Id;
                var rrfScore = 1.0 / (60 + i + 1);

                if (!fusionScores.ContainsKey(docId))
                {
                    fusionScores[docId] = 0;
                }

                fusionScores[docId] += rrfScore;
            }
        }

        // Re-rank all results by fusion score
        return allResults
            .GroupBy(r => r.Document.Id)
            .Select(g => g.First())  // Deduplicate
            .OrderByDescending(r => fusionScores[r.Document.Id])
            .ToList();
    }

    // Helper: Build context from multiple sources
    private string BuildMultiSourceContext(IEnumerable<SearchResult> results)
    {
        var contextBuilder = new StringBuilder();
        var docNumber = 1;

        foreach (var result in results)
        {
            var sourceType = result.Document.SourceType;
            var title = result.Document.Metadata["title"].ToString();

            contextBuilder.AppendLine($"[Document {docNumber} from {sourceType}: {title}]");
            contextBuilder.AppendLine(result.Document.Content);
            contextBuilder.AppendLine();

            docNumber++;
        }

        return contextBuilder.ToString();
    }
}
```

---

## Part 4: Complete Flow Diagram

```
USER: "What are our API guidelines?"
│
├─────────────────────────────────────────────────────────────┐
│ STEP 1: SOURCE SELECTION (LLM-based routing)               │
├─────────────────────────────────────────────────────────────┤
│ Available sources:                                          │
│   - Confluence (docs, wikis)                                │
│   - OneNote (meeting notes)                                 │
│   - SharePoint (files)                                      │
│   - SQL Database (structured data)                          │
│                                                              │
│ LLM analyzes query → Selects: [Confluence, SharePoint]     │
└────────────────────────────┬─────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 2: STRATEGY SELECTION                                  │
├─────────────────────────────────────────────────────────────┤
│ Query: "What are our API guidelines?"                       │
│ Analysis: Complex semantic question                         │
│ Decision: Use RAG for both sources                          │
└────────────────────────────┬─────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 3: GENERATE QUERY VARIATIONS                           │
├─────────────────────────────────────────────────────────────┤
│ 1. "API guidelines"                                         │
│ 2. "API design best practices"                              │
│ 3. "REST API standards"                                     │
└────────────────────────────┬─────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 4: GENERATE EMBEDDINGS                                 │
├─────────────────────────────────────────────────────────────┤
│ 3 queries × 1536 dimensions = 3 vectors                    │
└────────────────────────────┬─────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 5: PARALLEL VECTOR SEARCH (2 sources)                 │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────┐    ┌──────────────────────┐      │
│  │ Confluence Index     │    │ SharePoint Index     │      │
│  │ "confluence-vectors" │    │ "sharepoint-vectors" │      │
│  └──────────┬───────────┘    └──────────┬───────────┘      │
│             │                           │                    │
│     Search with 3 variations    Search with 3 variations    │
│             │                           │                    │
│    Returns 30 chunks           Returns 30 chunks            │
│             │                           │                    │
│             └───────────┬───────────────┘                    │
│                         │                                    │
│                 Total: 60 chunks                             │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 6: CROSS-SOURCE FUSION (Reciprocal Rank Fusion)       │
├─────────────────────────────────────────────────────────────┤
│ Combine rankings from both sources:                         │
│                                                              │
│ Top 20 results (mixed sources):                             │
│  1. confluence:ENG:12345:chunk:0    (RRF: 0.0484)          │
│  2. sharepoint:docs/api.docx:chunk:2 (RRF: 0.0451)         │
│  3. confluence:ENG:12345:chunk:1    (RRF: 0.0438)          │
│  4. confluence:ENG:12346:chunk:0    (RRF: 0.0421)          │
│  5. sharepoint:docs/rest.pdf:chunk:5 (RRF: 0.0398)         │
│  ... (15 more)                                              │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 7: RE-RANKING (Cohere)                                │
├─────────────────────────────────────────────────────────────┤
│ Score top 20 by relevance to original query                │
│ Returns top 5:                                              │
│  1. confluence:ENG:12345:chunk:0    (score: 0.95)          │
│  2. confluence:ENG:12345:chunk:1    (score: 0.89)          │
│  3. sharepoint:docs/api.docx:chunk:2 (score: 0.87)         │
│  4. confluence:ENG:12346:chunk:0    (score: 0.82)          │
│  5. sharepoint:docs/rest.pdf:chunk:5 (score: 0.79)         │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 8: BUILD MULTI-SOURCE CONTEXT                         │
├─────────────────────────────────────────────────────────────┤
│ [Document 1 from confluence: API Design Guidelines]        │
│ Our APIs follow REST principles...                          │
│                                                              │
│ [Document 2 from confluence: API Design Guidelines]        │
│ Versioning: All APIs must include version...                │
│                                                              │
│ [Document 3 from sharepoint: API Documentation Template]   │
│ All API documentation should include...                     │
│                                                              │
│ [Document 4 from confluence: API Standards]                │
│ Authentication: All APIs must use OAuth 2.0...              │
│                                                              │
│ [Document 5 from sharepoint: REST API Best Practices]      │
│ When designing REST APIs, consider...                       │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 9: LLM GENERATION (GPT-4)                             │
├─────────────────────────────────────────────────────────────┤
│ System: "Answer from multiple sources, cite each source"   │
│ Context: [5 documents from 2 sources]                       │
│ Question: "What are our API guidelines?"                    │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ RESULT                                                      │
├─────────────────────────────────────────────────────────────┤
│ Answer:                                                      │
│ "Our API guidelines are based on REST principles            │
│ [Source: Confluence]. Key requirements include:             │
│                                                              │
│ 1. Versioning: All APIs must include version in URL path    │
│    [Source: Confluence]                                      │
│                                                              │
│ 2. Authentication: Use OAuth 2.0 with JWT tokens            │
│    [Source: Confluence]                                      │
│                                                              │
│ 3. Documentation: Follow the API documentation template     │
│    [Source: SharePoint]                                      │
│                                                              │
│ When designing REST APIs, consider performance and          │
│ security best practices [Source: SharePoint]."              │
│                                                              │
│ Sources:                                                     │
│  - Confluence: API Design Guidelines (2 chunks)             │
│  - Confluence: API Standards (1 chunk)                      │
│  - SharePoint: API Documentation Template (1 chunk)         │
│  - SharePoint: REST API Best Practices (1 chunk)            │
│                                                              │
│ Metadata:                                                    │
│  - Sources searched: [confluence, sharepoint]               │
│  - Total chunks retrieved: 60                               │
│  - Final chunks used: 5                                     │
│  - Total time: 4,237ms                                      │
└─────────────────────────────────────────────────────────────┘
```

---

## Part 5: Configuration & Management

### appsettings.json

```json
{
  "QueryEngine": {
    "SourceSelection": {
      "Mode": "Hybrid",  // "Metadata", "Llm", or "Hybrid"
      "MaxSourcesPerQuery": 3,
      "AlwaysIncludeSources": [],  // Sources to always search
      "CacheSourceSelectionTtlMinutes": 60
    },
    "VectorSearch": {
      "TopKPerSource": 10,
      "RerankTopK": 20,
      "FinalContextChunks": 5
    }
  },

  "AzureSearch": {
    "Endpoint": "https://your-search.search.windows.net",
    "ApiKey": "your-key",
    "Indexes": {
      "Confluence": "confluence-vectors",
      "OneNote": "onenote-vectors",
      "SharePoint": "sharepoint-vectors",
      "SqlDatabase": "sqldatabase-vectors",
      "Notion": "notion-vectors"
    }
  },

  "DataSources": {
    "Confluence": {
      "Enabled": true,
      "Description": "Technical documentation, API guidelines, architecture docs",
      "IndexName": "confluence-vectors",
      "Priority": 1
    },
    "OneNote": {
      "Enabled": true,
      "Description": "Meeting notes, personal notes, project discussions",
      "IndexName": "onenote-vectors",
      "Priority": 2
    },
    "SharePoint": {
      "Enabled": true,
      "Description": "Files, documents, contracts, reports, presentations",
      "IndexName": "sharepoint-vectors",
      "Priority": 1
    },
    "SqlDatabase": {
      "Enabled": true,
      "Description": "Structured data, customer records, orders, sales data",
      "IndexName": "sqldatabase-vectors",
      "Priority": 3
    }
  }
}
```

---

## Part 6: Performance & Cost Analysis

### Single Source vs Multi-Source

| Metric | Single Source | 2 Sources | All 5 Sources |
|--------|--------------|-----------|---------------|
| **Source Selection Time** | 0ms (skip) | 150ms (LLM) | 150ms (LLM) |
| **Vector Search Time** | 200ms | 250ms (parallel) | 400ms (parallel) |
| **Chunks Retrieved** | 30 | 60 | 150 |
| **Fusion Time** | 50ms | 80ms | 150ms |
| **Re-ranking Time** | 100ms | 120ms | 180ms |
| **LLM Generation Time** | 2,000ms | 2,000ms | 2,000ms |
| **Total Time** | ~2.4s | ~2.6s | ~2.9s |
| **Cost per Query** | $0.04 | $0.05 | $0.07 |

**Key Insight:** Smart source selection (searching 2 sources instead of 5) saves:
- ⏱️ ~300ms latency
- 💰 ~$0.02 per query
- 🔋 Less compute/embedding costs

---

## Summary

### Storage Strategy
✅ **Separate vector indexes per source** for isolation and performance
✅ Each index: `{sourceType}-vectors` (e.g., "confluence-vectors")
✅ Same schema across all indexes for consistency

### Source Selection Strategy
✅ **3 approaches**: Metadata (fast), LLM (smart), Hybrid (best)
✅ Reduces search space from N sources to 1-3 relevant sources
✅ ~150ms overhead, but saves 300ms+ on vector search

### Query Orchestration
✅ **Parallel search** across selected sources
✅ **Cross-source fusion** with Reciprocal Rank Fusion
✅ **Multi-source context** with clear source attribution
✅ **Citations** showing which source each fact came from

### Benefits
- 🚀 Faster: Only search relevant sources
- 💰 Cheaper: Fewer embeddings and vector searches
- 🎯 More accurate: Better source selection = better results
- 📊 Transparent: Users see which sources were used

This architecture scales to 10, 20, or 100 data sources while maintaining performance!