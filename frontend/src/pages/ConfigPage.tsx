import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Save, RotateCcw } from 'lucide-react';
import { configApi } from '../api/client';
import { useStore } from '../store/useStore';
import { useTheme } from '../context/ThemeContext';
import type { RAGConfig } from '../types/index';

const ConfigPage = () => {
  const { theme } = useTheme();
  const { data: presets } = useQuery({
    queryKey: ['presets'],
    queryFn: () => configApi.getPresets(),
  });

  const { data: defaultConfig } = useQuery({
    queryKey: ['defaultConfig'],
    queryFn: () => configApi.getDefault(),
  });

  const { data: availableModels } = useQuery({
    queryKey: ['availableModels'],
    queryFn: () => configApi.getModels(),
  });

  const currentConfig = useStore((state) => state.currentConfig);
  const setCurrentConfig = useStore((state) => state.setCurrentConfig);

  const [config, setConfig] = useState<RAGConfig | null>(null);

  useEffect(() => {
    if (currentConfig) {
      setConfig(currentConfig);
    } else if (defaultConfig?.data) {
      setConfig(defaultConfig.data);
    }
  }, [currentConfig, defaultConfig]);

  const loadPreset = (presetName: string) => {
    if (presets) {
      setConfig(presets.data[presetName]);
    }
  };

  const saveConfig = () => {
    if (config) {
      setCurrentConfig(config);
      alert('Configuration saved!');
    }
  };

  const resetToDefault = () => {
    if (defaultConfig) {
      setConfig(defaultConfig.data);
      setCurrentConfig(defaultConfig.data);
    }
  };

  if (!config) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-claude-primary mx-auto mb-4"></div>
          <p className="text-claude-text-secondary">Loading configuration...</p>
        </div>
      </div>
    );
  }

  const containerHeight = theme === 'claude' ? 'h-[calc(100vh-64px)]' : 'h-[calc(100vh-80px)]';

  return (
    <div className={`${containerHeight} overflow-y-auto`}>
      <div className="max-w-7xl mx-auto p-6">
        {/* Compact Header with Actions */}
        <div className="bg-white rounded-lg shadow-sm p-4 mb-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold">RAG Configuration</h2>
              <p className="text-sm text-gray-600">Configure settings and advanced techniques</p>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={resetToDefault}
                className="flex items-center gap-2 px-3 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 text-sm"
              >
                <RotateCcw size={16} />
                Reset
              </button>
              <button
                onClick={saveConfig}
                className="flex items-center gap-2 px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm"
              >
                <Save size={16} />
                Save
              </button>
            </div>
          </div>
        </div>

        {/* Horizontal Presets Row */}
        <div className="bg-white rounded-lg shadow-sm p-4 mb-4">
          <h3 className="text-sm font-semibold mb-3">Quick Presets</h3>
          <div className="grid grid-cols-4 gap-3">
            {presets &&
              Object.keys(presets.data).map((presetName) => (
                <button
                  key={presetName}
                  onClick={() => loadPreset(presetName)}
                  className="px-4 py-3 text-left border-2 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-colors"
                >
                  <div className="font-medium capitalize text-sm">{presetName}</div>
                  <div className="text-xs text-gray-500 mt-1">
                    {getPresetDescription(presetName)}
                  </div>
                </button>
              ))}
          </div>
        </div>

        {/* Basic Settings - Compact Grid */}
        <div className="bg-white rounded-lg shadow-sm p-4 mb-4">
          <h3 className="text-sm font-semibold mb-3">Basic Settings</h3>
          <div className="grid grid-cols-4 gap-4">
            <div>
              <label className="block text-xs font-medium mb-2">
                Chunk Size: <span className="text-blue-600">{config.chunk_size}</span>
              </label>
              <input
                type="range"
                min="100"
                max="2000"
                step="100"
                value={config.chunk_size}
                onChange={(e) =>
                  setConfig({ ...config, chunk_size: parseInt(e.target.value) })
                }
                className="w-full"
              />
            </div>
            <div>
              <label className="block text-xs font-medium mb-2">
                Overlap: <span className="text-blue-600">{config.chunk_overlap}</span>
              </label>
              <input
                type="range"
                min="0"
                max="500"
                step="50"
                value={config.chunk_overlap}
                onChange={(e) =>
                  setConfig({ ...config, chunk_overlap: parseInt(e.target.value) })
                }
                className="w-full"
              />
            </div>
            <div>
              <label className="block text-xs font-medium mb-2">
                Retrieval K: <span className="text-blue-600">{config.retrieval_k}</span>
              </label>
              <input
                type="range"
                min="1"
                max="20"
                step="1"
                value={config.retrieval_k}
                onChange={(e) =>
                  setConfig({ ...config, retrieval_k: parseInt(e.target.value) })
                }
                className="w-full"
              />
            </div>
            <div>
              <label className="block text-xs font-medium mb-2">
                Temperature: <span className="text-blue-600">{config.temperature}</span>
              </label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.1"
                value={config.temperature}
                onChange={(e) =>
                  setConfig({ ...config, temperature: parseFloat(e.target.value) })
                }
                className="w-full"
              />
            </div>
          </div>
          <div className="mt-4">
            <label className="block text-xs font-medium mb-2">Model</label>
            <div className="grid grid-cols-2 gap-3">
              <select
                value={config.model_name}
                onChange={(e) =>
                  setConfig({ ...config, model_name: e.target.value })
                }
                className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm"
              >
                {availableModels?.data.map((model) => (
                  <option key={model} value={model}>
                    {model}
                  </option>
                ))}
              </select>
              <div className="flex items-center text-xs text-gray-500 px-2">
                {getModelDescription(config.model_name)}
              </div>
            </div>
          </div>
        </div>

        {/* Advanced Techniques - 2 Column Grid */}
        <div className="bg-white rounded-lg shadow-sm p-4">
          <h3 className="text-sm font-semibold mb-3">Advanced RAG Techniques</h3>
          <div className="grid grid-cols-2 gap-3">
            {/* Multi-Query */}
            <TechniqueCard
              title="Multi-Query"
              description="Multiple query perspectives"
              enabled={config.multi_query.enabled}
              onToggle={(enabled) =>
                setConfig({
                  ...config,
                  multi_query: { ...config.multi_query, enabled },
                })
              }
            >
              <div>
                <label className="block text-xs mb-2">
                  Queries: {config.multi_query.num_queries}
                </label>
                <input
                  type="range"
                  min="2"
                  max="10"
                  value={config.multi_query.num_queries}
                  onChange={(e) =>
                    setConfig({
                      ...config,
                      multi_query: {
                        ...config.multi_query,
                        num_queries: parseInt(e.target.value),
                      },
                    })
                  }
                  className="w-full"
                />
              </div>
            </TechniqueCard>

            {/* RAG-Fusion */}
            <TechniqueCard
              title="RAG-Fusion"
              description="Reciprocal Rank Fusion"
              enabled={config.rag_fusion.enabled}
              onToggle={(enabled) =>
                setConfig({
                  ...config,
                  rag_fusion: { ...config.rag_fusion, enabled },
                })
              }
            >
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs mb-2">
                    Queries: {config.rag_fusion.num_queries}
                  </label>
                  <input
                    type="range"
                    min="2"
                    max="10"
                    value={config.rag_fusion.num_queries}
                    onChange={(e) =>
                      setConfig({
                        ...config,
                        rag_fusion: {
                          ...config.rag_fusion,
                          num_queries: parseInt(e.target.value),
                        },
                      })
                    }
                    className="w-full"
                  />
                </div>
                <div>
                  <label className="block text-xs mb-2">
                    RRF K: {config.rag_fusion.rrf_k}
                  </label>
                  <input
                    type="range"
                    min="1"
                    max="100"
                    value={config.rag_fusion.rrf_k}
                    onChange={(e) =>
                      setConfig({
                        ...config,
                        rag_fusion: {
                          ...config.rag_fusion,
                          rrf_k: parseInt(e.target.value),
                        },
                      })
                    }
                    className="w-full"
                  />
                </div>
              </div>
            </TechniqueCard>

            {/* Decomposition */}
            <TechniqueCard
              title="Decomposition"
              description="Break into sub-questions"
              enabled={config.decomposition.enabled}
              onToggle={(enabled) =>
                setConfig({
                  ...config,
                  decomposition: { ...config.decomposition, enabled },
                })
              }
            >
              <div>
                <label className="block text-xs mb-2">Mode</label>
                <select
                  value={config.decomposition.mode}
                  onChange={(e) =>
                    setConfig({
                      ...config,
                      decomposition: {
                        ...config.decomposition,
                        mode: e.target.value as 'recursive' | 'individual',
                      },
                    })
                  }
                  className="w-full px-2 py-1.5 border rounded-lg text-sm"
                >
                  <option value="recursive">Recursive</option>
                  <option value="individual">Individual</option>
                </select>
              </div>
            </TechniqueCard>

            {/* Step-Back */}
            <TechniqueCard
              title="Step-Back"
              description="Broader questions for context"
              enabled={config.step_back.enabled}
              onToggle={(enabled) =>
                setConfig({
                  ...config,
                  step_back: { ...config.step_back, enabled },
                })
              }
            />

            {/* HyDE */}
            <TechniqueCard
              title="HyDE"
              description="Hypothetical embeddings"
              enabled={config.hyde.enabled}
              onToggle={(enabled) =>
                setConfig({
                  ...config,
                  hyde: { enabled },
                })
              }
            />

            {/* Re-ranking */}
            <TechniqueCard
              title="Re-ranking"
              description="Re-rank with Cohere"
              enabled={config.reranking.enabled}
              onToggle={(enabled) =>
                setConfig({
                  ...config,
                  reranking: { ...config.reranking, enabled },
                })
              }
            >
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs mb-2">
                    Top K: {config.reranking.top_k}
                  </label>
                  <input
                    type="range"
                    min="5"
                    max="20"
                    value={config.reranking.top_k}
                    onChange={(e) =>
                      setConfig({
                        ...config,
                        reranking: {
                          ...config.reranking,
                          top_k: parseInt(e.target.value),
                        },
                      })
                    }
                    className="w-full"
                  />
                </div>
                <div>
                  <label className="block text-xs mb-2">
                    Top N: {config.reranking.top_n}
                  </label>
                  <input
                    type="range"
                    min="1"
                    max="10"
                    value={config.reranking.top_n}
                    onChange={(e) =>
                      setConfig({
                        ...config,
                        reranking: {
                          ...config.reranking,
                          top_n: parseInt(e.target.value),
                        },
                      })
                    }
                    className="w-full"
                  />
                </div>
              </div>
            </TechniqueCard>
          </div>
        </div>
      </div>
    </div>
  );
};

const TechniqueCard = ({
  title,
  description,
  enabled,
  onToggle,
  children,
}: {
  title: string;
  description: string;
  enabled: boolean;
  onToggle: (enabled: boolean) => void;
  children?: React.ReactNode;
}) => {
  return (
    <div className="border rounded-lg p-3">
      <div className="flex items-start justify-between mb-1">
        <div className="flex-1">
          <h4 className="font-medium text-sm">{title}</h4>
          <p className="text-xs text-gray-600 mt-0.5">{description}</p>
        </div>
        <label className="relative inline-flex items-center cursor-pointer ml-3">
          <input
            type="checkbox"
            checked={enabled}
            onChange={(e) => onToggle(e.target.checked)}
            className="sr-only peer"
          />
          <div className="w-9 h-5 bg-gray-200 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-blue-600"></div>
        </label>
      </div>
      {enabled && children && <div className="mt-3 pt-3 border-t">{children}</div>}
    </div>
  );
};

const getPresetDescription = (name: string) => {
  const descriptions: Record<string, string> = {
    fast: 'Basic RAG - Fast and simple',
    balanced: 'Multi-query + Re-ranking',
    quality: 'Multiple techniques - Best quality',
    research: 'Decomposition + Step-back',
  };
  return descriptions[name] || '';
};

const getModelDescription = (modelName: string) => {
  const descriptions: Record<string, string> = {
    'gpt-4o': 'Latest GPT-4 Omni - Best quality, higher cost',
    'gpt-4o-mini': 'Cost-effective GPT-4 Omni - Great balance',
    'gpt-4-turbo': 'GPT-4 Turbo - Fast and capable',
    'gpt-4': 'Standard GPT-4 - Reliable performance',
    'gpt-3.5-turbo': 'GPT-3.5 Turbo - Fast and economical',
  };
  return descriptions[modelName] || 'Custom model';
};

export default ConfigPage;
