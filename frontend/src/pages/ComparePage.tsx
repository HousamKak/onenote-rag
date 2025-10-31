import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Send, Loader2, Clock, Zap } from 'lucide-react';
import { queryApi } from '../api/client';

const ComparePage = () => {
  const [question, setQuestion] = useState('');
  const [selectedConfigs, setSelectedConfigs] = useState<string[]>([
    'fast',
    'balanced',
  ]);

  const compareMutation = useMutation({
    mutationFn: (question: string) =>
      queryApi.compare(question, selectedConfigs),
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (question.trim() && selectedConfigs.length > 0) {
      compareMutation.mutate(question.trim());
    }
  };

  const presets = ['fast', 'balanced', 'quality', 'research'];

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="bg-white rounded-lg shadow-sm p-6">
        <h2 className="text-xl font-semibold mb-4">Compare Configurations</h2>
        <p className="text-gray-600 mb-6">
          Test the same question with different RAG configurations and compare
          results side-by-side.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-2">
              Select Configurations to Compare
            </label>
            <div className="grid grid-cols-4 gap-3">
              {presets.map((preset) => (
                <label
                  key={preset}
                  className={`flex items-center justify-center px-4 py-3 border-2 rounded-lg cursor-pointer transition-colors ${
                    selectedConfigs.includes(preset)
                      ? 'border-blue-600 bg-blue-50'
                      : 'border-gray-300 hover:border-gray-400'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={selectedConfigs.includes(preset)}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setSelectedConfigs([...selectedConfigs, preset]);
                      } else {
                        setSelectedConfigs(
                          selectedConfigs.filter((c) => c !== preset)
                        );
                      }
                    }}
                    className="mr-2"
                  />
                  <span className="font-medium capitalize">{preset}</span>
                </label>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">Question</label>
            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask a question to compare across configurations..."
              className="w-full px-4 py-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
              rows={4}
              disabled={compareMutation.isPending}
            />
          </div>

          <button
            type="submit"
            disabled={
              !question.trim() ||
              selectedConfigs.length === 0 ||
              compareMutation.isPending
            }
            className="flex items-center gap-2 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
          >
            {compareMutation.isPending ? (
              <>
                <Loader2 size={20} className="animate-spin" />
                Comparing...
              </>
            ) : (
              <>
                <Send size={20} />
                Compare
              </>
            )}
          </button>
        </form>
      </div>

      {/* Results */}
      {compareMutation.data && (
        <div className="grid grid-cols-2 gap-6">
          {compareMutation.data.data.results.map((result: any, idx: number) => (
            <div key={idx} className="bg-white rounded-lg shadow-sm overflow-hidden">
              {/* Header */}
              <div className="bg-gray-50 border-b px-6 py-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-semibold capitalize">
                    {result.config_name}
                  </h3>
                  <div className="flex items-center gap-2 text-sm text-gray-600">
                    <Clock size={16} />
                    {result.metadata.latency_ms}ms
                  </div>
                </div>
                <div className="flex gap-2 mt-2">
                  {result.metadata.techniques_used.map((tech: string) => (
                    <span
                      key={tech}
                      className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs font-medium"
                    >
                      {tech}
                    </span>
                  ))}
                </div>
              </div>

              {/* Answer */}
              <div className="p-6">
                <div className="prose max-w-none text-gray-700 text-sm whitespace-pre-wrap">
                  {result.answer}
                </div>
              </div>

              {/* Metrics */}
              <div className="border-t bg-gray-50 px-6 py-3">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-600">Model:</span>{' '}
                    <span className="font-medium">{result.metadata.model_name}</span>
                  </div>
                  <div>
                    <span className="text-gray-600">Docs:</span>{' '}
                    <span className="font-medium">{result.metadata.retrieval_k}</span>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {compareMutation.error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <h3 className="font-semibold text-red-800 mb-2">Error</h3>
          <p className="text-red-600">
            {(compareMutation.error as any).message ||
              'An error occurred during comparison'}
          </p>
        </div>
      )}
    </div>
  );
};

export default ComparePage;
