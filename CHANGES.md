# Configuration Updates - GPT-4o-mini & Model Selector

## Changes Made

### 1. Backend Updates

#### `backend/models/rag_config.py`
- ✅ Added `AVAILABLE_MODELS` list with all supported OpenAI models:
  - `gpt-4o` (Latest GPT-4 Omni)
  - `gpt-4o-mini` (Cost-effective, **NEW DEFAULT**)
  - `gpt-4-turbo` (GPT-4 Turbo)
  - `gpt-4` (Standard GPT-4)
  - `gpt-3.5-turbo` (GPT-3.5 Turbo)

- ✅ Updated default model from `gpt-3.5-turbo` to `gpt-4o-mini`
- ✅ Updated preset configurations:
  - **Fast**: `gpt-4o-mini` (was `gpt-3.5-turbo`)
  - **Balanced**: `gpt-4o-mini` (was `gpt-3.5-turbo`)
  - **Quality**: `gpt-4o` (was `gpt-4-turbo-preview`)
  - **Research**: `gpt-4o` (was `gpt-4-turbo-preview`)

#### `backend/api/routes.py`
- ✅ Added new endpoint: `GET /api/config/models`
  - Returns list of available models
  - Can be used to populate dropdowns in UI

### 2. Frontend Updates

#### `frontend/src/api/client.ts`
- ✅ Added `getModels()` method to `configApi`

#### `frontend/src/pages/ConfigPage.tsx`
- ✅ Added model selector dropdown in Basic Settings
- ✅ Fetches available models from backend API
- ✅ Shows model descriptions on selection:
  - gpt-4o: "Latest GPT-4 Omni - Best quality, higher cost"
  - gpt-4o-mini: "Cost-effective GPT-4 Omni - Great balance"
  - gpt-4-turbo: "GPT-4 Turbo - Fast and capable"
  - gpt-4: "Standard GPT-4 - Reliable performance"
  - gpt-3.5-turbo: "GPT-3.5 Turbo - Fast and economical"

#### `frontend/src/store/useStore.ts`
- ✅ Fixed import to use `type` keyword for better TypeScript compatibility

## Why GPT-4o-mini?

**GPT-4o-mini** is the recommended default because:
1. **Cost-Effective**: 60% cheaper than GPT-3.5-turbo
2. **Better Quality**: Outperforms GPT-3.5-turbo on most benchmarks
3. **Fast**: Similar latency to GPT-3.5-turbo
4. **Latest**: Most recent optimized model from OpenAI
5. **Great Balance**: Best price/performance ratio

## Model Comparison

| Model | Speed | Quality | Cost/1M tokens | Use Case |
|-------|-------|---------|---------------|----------|
| gpt-4o | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | $15 | Maximum quality |
| gpt-4o-mini | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | $0.60 | **Best default** |
| gpt-4-turbo | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | $10 | High quality |
| gpt-4 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | $30 | Premium quality |
| gpt-3.5-turbo | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | $1.50 | Budget option |

## How to Use

### From UI
1. Go to **Configuration** page
2. In **Basic Settings**, find the **Model** dropdown
3. Select your desired model
4. See the description update automatically
5. Click **Save Configuration**

### From API
```python
# Query with specific model
response = requests.post("http://localhost:8000/api/query", json={
    "question": "What is RAG?",
    "config": {
        "model_name": "gpt-4o-mini",  # or any other model
        "chunk_size": 1000,
        "retrieval_k": 4,
        "temperature": 0.0,
        # ... other settings
    }
})
```

### Get Available Models
```bash
curl http://localhost:8000/api/config/models
# Returns: ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"]
```

## Testing

1. **Start Backend**:
   ```bash
   cd backend
   python main.py
   ```

2. **Start Frontend**:
   ```bash
   cd frontend
   npm run dev
   ```

3. **Test Model Selector**:
   - Open http://localhost:5173/config
   - See model dropdown populated
   - Change models and see descriptions
   - Save and test queries

4. **Test API**:
   ```bash
   # Get available models
   curl http://localhost:8000/api/config/models

   # Get presets (now using gpt-4o-mini)
   curl http://localhost:8000/api/config/presets
   ```

## Migration Notes

### If You Had Custom Configs
- Old configs with `gpt-3.5-turbo` will still work
- Consider switching to `gpt-4o-mini` for better quality at similar cost
- The UI now lets you change models easily

### If You're Using Presets
- All presets automatically updated
- Fast/Balanced now use `gpt-4o-mini`
- Quality/Research now use full `gpt-4o`
- No code changes needed

## Next Steps

### Optional Enhancements
1. **Add model info tooltips** with pricing details
2. **Show estimated cost** per query based on model
3. **Add model performance metrics** from testing
4. **Allow custom models** by typing model name

### Future Models
When OpenAI releases new models:
1. Add to `AVAILABLE_MODELS` list in `backend/models/rag_config.py`
2. Add description in `frontend/src/pages/ConfigPage.tsx`
3. Model will automatically appear in dropdown

## Rollback (If Needed)

To revert to GPT-3.5-turbo default:

```python
# backend/models/rag_config.py
model_name: str = Field("gpt-3.5-turbo", description="LLM model name")
```

## Summary

✅ System now defaults to **GPT-4o-mini** (better quality, similar cost)
✅ Users can **select models from UI dropdown**
✅ **5 models available** for different use cases
✅ **Descriptions shown** to help users choose
✅ **All presets updated** with optimal models
✅ **Backward compatible** with old configs

**Result**: More flexible, better default model, user-friendly configuration!
