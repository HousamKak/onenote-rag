import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Send, Loader2, ExternalLink, Clock, Zap } from 'lucide-react';
import { queryApi } from '../api/client';
import { useStore } from '../store/useStore';
import type { QueryResponse } from '../types/index';

const QueryPage = () => {
  const [question, setQuestion] = useState('');
  const currentConfig = useStore((state) => state.currentConfig);
  const addQueryToHistory = useStore((state) => state.addQueryToHistory);

  const queryMutation = useMutation({
    mutationFn: (question: string) =>
      queryApi.query({ question, config: currentConfig || undefined }),
    onSuccess: (response) => {
      addQueryToHistory(response.data);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (question.trim()) {
      queryMutation.mutate(question.trim());
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="bg-white rounded-lg shadow-sm p-6">
        <h2 className="text-xl font-semibold mb-4">Ask a Question</h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask a question about your OneNote documents..."
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
              rows={4}
              disabled={queryMutation.isPending}
            />
          </div>

          <div className="flex items-center justify-between">
            <div className="text-sm text-gray-600">
              {currentConfig ? (
                <span className="flex items-center gap-2">
                  <Zap size={16} className="text-blue-600" />
                  Using custom configuration
                </span>
              ) : (
                <span>Using default configuration</span>
              )}
            </div>
            <button
              type="submit"
              disabled={!question.trim() || queryMutation.isPending}
              className="flex items-center gap-2 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
            >
              {queryMutation.isPending ? (
                <>
                  <Loader2 size={20} className="animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <Send size={20} />
                  Ask
                </>
              )}
            </button>
          </div>
        </form>
      </div>

      {/* Result */}
      {queryMutation.data && (
        <AnswerCard response={queryMutation.data.data} />
      )}

      {/* Error */}
      {queryMutation.error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <h3 className="font-semibold text-red-800 mb-2">Error</h3>
          <p className="text-red-600">
            {queryMutation.error.message || 'An error occurred while processing your query'}
          </p>
        </div>
      )}
    </div>
  );
};

const AnswerCard = ({ response }: { response: QueryResponse }) => {
  return (
    <div className="bg-white rounded-lg shadow-sm overflow-hidden">
      {/* Metadata Bar */}
      <div className="bg-gray-50 border-b px-6 py-3 flex items-center justify-between text-sm">
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-1 text-gray-600">
            <Clock size={16} />
            {response.metadata.latency_ms}ms
          </span>
          <span className="text-gray-600">
            Model: {response.metadata.model_name}
          </span>
          <span className="text-gray-600">
            Retrieved: {response.metadata.retrieval_k} docs
          </span>
        </div>
        <div className="flex gap-2">
          {response.metadata.techniques_used.map((technique) => (
            <span
              key={technique}
              className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs font-medium"
            >
              {technique}
            </span>
          ))}
        </div>
      </div>

      {/* Answer */}
      <div className="p-6">
        <h3 className="text-lg font-semibold mb-3">Answer</h3>
        <div className="prose max-w-none text-gray-700 whitespace-pre-wrap">
          {response.answer}
        </div>
      </div>

      {/* Sources */}
      {response.sources.length > 0 && (
        <div className="border-t px-6 py-4">
          <h3 className="text-lg font-semibold mb-3">Sources</h3>
          <div className="space-y-3">
            {response.sources.map((source, idx) => (
              <div
                key={idx}
                className="p-4 bg-gray-50 rounded-lg border border-gray-200"
              >
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <h4 className="font-medium text-gray-900">
                      {source.page_title}
                    </h4>
                    <p className="text-sm text-gray-600">
                      {source.notebook_name} → {source.section_name}
                    </p>
                  </div>
                  {source.url && (
                    <a
                      href={source.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:text-blue-800"
                    >
                      <ExternalLink size={18} />
                    </a>
                  )}
                </div>
                <p className="text-sm text-gray-700">{source.content_snippet}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default QueryPage;
