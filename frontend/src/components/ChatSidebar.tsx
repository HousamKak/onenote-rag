import { ChevronRight, Settings, Database, Zap } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';
import { useStore } from '../store/useStore';
import { useQuery } from '@tanstack/react-query';
import { indexApi } from '../api/client';

interface ChatSidebarProps {
  isOpen: boolean;
  onToggle: () => void;
}

const ChatSidebar = ({ isOpen, onToggle }: ChatSidebarProps) => {
  const { theme } = useTheme();
  const { currentConfig } = useStore();

  // Fetch index stats
  const { data: stats } = useQuery({
    queryKey: ['indexStats'],
    queryFn: () => indexApi.getStats(),
    refetchInterval: 30000, // Refresh every 30s
  });

  // Normalize stats shape: some query functions return AxiosResponse (with `.data`) and
  // others may return the raw data object. Handle both safely and provide fallbacks.
  const totalDocuments =
    // AxiosResponse shape
    (stats as any)?.data?.total_documents ??
    // raw data shape
    (stats as any)?.total_documents ??
    0;

  const collectionName =
    (stats as any)?.data?.collection_name ??
    (stats as any)?.collection_name ??
    'N/A';

  const presets = [
    { name: 'fast', label: 'Fast', emoji: '⚡', color: theme === 'claude' ? 'bg-green-100 text-green-800' : 'bg-neo-lime' },
    { name: 'balanced', label: 'Balanced', emoji: '⚖️', color: theme === 'claude' ? 'bg-blue-100 text-blue-800' : 'bg-neo-cyan' },
    { name: 'quality', label: 'Quality', emoji: '✨', color: theme === 'claude' ? 'bg-purple-100 text-purple-800' : 'bg-neo-pink' },
    { name: 'research', label: 'Research', emoji: '🔬', color: theme === 'claude' ? 'bg-orange-100 text-orange-800' : 'bg-neo-orange' },
  ];

  const activeTechniques = currentConfig
    ? [
        currentConfig.multi_query?.enabled && 'Multi-Query',
        currentConfig.rag_fusion?.enabled && 'RAG Fusion',
        currentConfig.decomposition?.enabled && 'Decomposition',
        currentConfig.step_back?.enabled && 'Step-Back',
        currentConfig.hyde?.enabled && 'HyDE',
        currentConfig.reranking?.enabled && 'Re-ranking',
      ].filter((t): t is string => typeof t === 'string')
    : [];

  if (theme === 'claude') {
    return (
      <>
        {/* Toggle Button */}
        <button
          onClick={onToggle}
          className={`fixed top-20 right-0 z-50 p-2 bg-claude-accent text-white rounded-l-lg shadow-lg hover:bg-claude-accent-hover transition-all ${
            isOpen ? 'translate-x-0' : 'translate-x-0'
          }`}
          title={isOpen ? 'Hide sidebar' : 'Show sidebar'}
        >
          <ChevronRight
            size={20}
            className={`transition-transform ${isOpen ? 'rotate-180' : ''}`}
          />
        </button>

        {/* Sidebar */}
        <div
          className={`fixed top-16 right-0 h-[calc(100vh-64px)] w-80 bg-white border-l border-claude-border shadow-lg overflow-y-auto transition-transform z-40 ${
            isOpen ? 'translate-x-0' : 'translate-x-full'
          }`}
        >
          <div className="p-4 space-y-6">
            {/* Header */}
            <div className="flex items-center gap-2 pb-4 border-b border-claude-border">
              <Settings size={20} className="text-claude-accent" />
              <h3 className="font-semibold text-claude-text">RAG Settings</h3>
            </div>

            {/* Document Stats */}
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-sm font-medium text-claude-text-secondary">
                <Database size={16} />
                <span>Document Stats</span>
              </div>
              <div className="bg-claude-bg rounded-lg p-3 space-y-2 hover-lift transition-all">
                <div className="flex justify-between text-sm">
                  <span className="text-claude-text-secondary">Indexed Chunks:</span>
                  <span className="font-medium text-claude-text animate-pulse">
                    {totalDocuments}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-claude-text-secondary">Collection:</span>
                  <span className="font-medium text-claude-text text-xs">
                    {collectionName}
                  </span>
                </div>
              </div>
            </div>

            {/* Current Config */}
            {currentConfig && (
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-sm font-medium text-claude-text-secondary">
                  <Zap size={16} />
                  <span>Active Config</span>
                </div>
                <div className="bg-claude-bg rounded-lg p-3 space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-claude-text-secondary">Model:</span>
                    <span className="font-medium text-claude-text text-xs">
                      {currentConfig.model_name}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-claude-text-secondary">Temperature:</span>
                    <span className="font-medium text-claude-text">
                      {currentConfig.temperature}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-claude-text-secondary">Retrieval K:</span>
                    <span className="font-medium text-claude-text">
                      {currentConfig.retrieval_k}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-claude-text-secondary">Chunk Size:</span>
                    <span className="font-medium text-claude-text">
                      {currentConfig.chunk_size}
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* Active Techniques */}
            {activeTechniques.length > 0 && (
              <div className="space-y-2">
                <div className="text-sm font-medium text-claude-text-secondary">
                  Active Techniques
                </div>
                <div className="flex flex-wrap gap-2">
                  {activeTechniques.map((technique) => (
                    <span
                      key={technique}
                      className="px-2 py-1 bg-claude-accent text-white rounded text-xs font-medium"
                    >
                      {technique}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Quick Presets */}
            <div className="space-y-2">
              <div className="text-sm font-medium text-claude-text-secondary">
                Quick Presets
              </div>
              <div className="grid grid-cols-2 gap-2">
                {presets.map((preset) => (
                  <button
                    key={preset.name}
                    onClick={() => {
                      // TODO: Load preset config
                      console.log('Load preset:', preset.name);
                    }}
                    className={`p-3 rounded-lg border border-claude-border hover:border-claude-accent transition-all hover-lift text-left ${preset.color}`}
                  >
                    <div className="text-lg mb-1">{preset.emoji}</div>
                    <div className="text-xs font-medium">{preset.label}</div>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      </>
    );
  }

  // Brutalist theme
  return (
    <>
      {/* Toggle Button */}
      <button
        onClick={onToggle}
        className={`fixed top-24 right-0 z-50 p-3 bg-neo-pink border-4 border-neo-black shadow-brutal hover:shadow-brutal-hover hover:translate-x-[-4px] hover:translate-y-1 active:shadow-none active:translate-x-[-8px] active:translate-y-2 transition-all ${
          isOpen ? 'translate-x-0' : 'translate-x-0'
        }`}
        title={isOpen ? 'Hide sidebar' : 'Show sidebar'}
      >
        <ChevronRight
          size={24}
          strokeWidth={3}
          className={`transition-transform text-neo-black ${isOpen ? 'rotate-180' : ''}`}
        />
      </button>

      {/* Sidebar */}
      <div
        className={`fixed top-16 right-0 h-[calc(100vh-64px)] w-80 bg-white border-l border-claude-border shadow-lg overflow-y-auto transition-all duration-300 ease-in-out z-40 ${
          isOpen ? 'translate-x-0' : 'translate-x-full'
        }`}
      >
        <div className="p-4 space-y-6 animate-fadeIn">
          {/* Header */}
          <div className="flex items-center gap-2 pb-4 border-b-4 border-neo-black">
            <Settings size={24} strokeWidth={3} className="text-neo-black" />
            <h3 className="font-black text-neo-black uppercase text-lg">RAG Settings</h3>
          </div>

          {/* Document Stats */}
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm font-black text-neo-black uppercase">
              <Database size={18} strokeWidth={3} />
              <span>Document Stats</span>
            </div>
            <div className="bg-neo-yellow border-4 border-neo-black shadow-brutal p-3 space-y-2">
              <div className="flex justify-between text-sm font-bold">
                <span className="text-neo-black">CHUNKS:</span>
                <span className="font-black text-neo-black">
                  {totalDocuments}
                </span>
              </div>
              <div className="flex justify-between text-xs font-bold">
                <span className="text-neo-black">COLLECTION:</span>
                <span className="font-black text-neo-black truncate ml-2">
                  {collectionName}
                </span>
              </div>
            </div>
          </div>

          {/* Current Config */}
          {currentConfig && (
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-sm font-black text-neo-black uppercase">
                <Zap size={18} strokeWidth={3} />
                <span>Active Config</span>
              </div>
              <div className="bg-neo-cyan border-4 border-neo-black shadow-brutal p-3 space-y-2">
                <div className="flex justify-between text-xs font-bold">
                  <span className="text-neo-black">MODEL:</span>
                  <span className="font-black text-neo-black text-xs">
                    {currentConfig.model_name}
                  </span>
                </div>
                <div className="flex justify-between text-xs font-bold">
                  <span className="text-neo-black">TEMP:</span>
                  <span className="font-black text-neo-black">
                    {currentConfig.temperature}
                  </span>
                </div>
                <div className="flex justify-between text-xs font-bold">
                  <span className="text-neo-black">K:</span>
                  <span className="font-black text-neo-black">
                    {currentConfig.retrieval_k}
                  </span>
                </div>
                <div className="flex justify-between text-xs font-bold">
                  <span className="text-neo-black">CHUNK:</span>
                  <span className="font-black text-neo-black">
                    {currentConfig.chunk_size}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Active Techniques */}
          {activeTechniques.length > 0 && (
            <div className="space-y-2">
              <div className="text-sm font-black text-neo-black uppercase">
                Active Techniques
              </div>
              <div className="flex flex-wrap gap-2">
                {activeTechniques.map((technique) => (
                  <span
                    key={technique}
                    className="px-2 py-1 bg-neo-lime text-neo-black border-2 border-neo-black text-xs font-black uppercase"
                  >
                    {technique}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Quick Presets */}
          <div className="space-y-2">
            <div className="text-sm font-black text-neo-black uppercase">
              Quick Presets
            </div>
            <div className="grid grid-cols-2 gap-2">
              {presets.map((preset) => (
                <button
                  key={preset.name}
                  onClick={() => {
                    // TODO: Load preset config
                    console.log('Load preset:', preset.name);
                  }}
                  className={`p-3 border-4 border-neo-black shadow-brutal hover:shadow-brutal-hover hover:translate-x-1 hover:translate-y-1 active:shadow-none active:translate-x-2 active:translate-y-2 text-left ${preset.color}`}
                >
                  <div className="text-2xl mb-1">{preset.emoji}</div>
                  <div className="text-xs font-black text-neo-black uppercase">{preset.label}</div>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </>
  );
};

export default ChatSidebar;
