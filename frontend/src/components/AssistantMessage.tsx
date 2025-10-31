import { useState } from 'react';
import { ExternalLink, Clock, ChevronDown, ChevronUp, Copy, Check } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useTheme } from '../context/ThemeContext';
import type { Message } from '../types/index';

interface AssistantMessageProps {
  message: Message;
}

const AssistantMessage = ({ message }: AssistantMessageProps) => {
  const { theme } = useTheme();
  const [showSources, setShowSources] = useState(false);
  const [showMetadata, setShowMetadata] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const hasSources = message.sources && message.sources.length > 0;
  const hasMetadata = message.metadata;

  if (theme === 'claude') {
    return (
      <div className="flex items-start max-w-3xl animate-fadeInUp">
        <div className="flex-1 min-w-0">
          <div className="bg-claude-surface rounded-2xl px-4 py-3 shadow-claude hover-lift">
            <div className="prose max-w-none">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  a: ({ node, ...props }) => (
                    // open links in new tab
                    // eslint-disable-next-line jsx-a11y/anchor-has-content
                    <a {...props} target="_blank" rel="noopener noreferrer" className="text-claude-primary hover:underline" />
                  ),
                  code: ({ node, className, children, ...props }) => {
                    const isInline = !className;
                    if (isInline) {
                      return <code className="bg-claude-bg-accent px-1 rounded text-sm" {...props}>{children}</code>;
                    }
                    // block code
                    return (
                      <pre className="rounded bg-claude-bg-accent p-3 overflow-auto text-sm"><code className={className} {...props}>{children}</code></pre>
                    );
                  }
                }}
              >
                {message.content}
              </ReactMarkdown>
            </div>

            {/* Action buttons */}
            <div className="flex items-center gap-2 mt-3 pt-3 border-t border-gray-100">
              <button
                onClick={handleCopy}
                className="text-claude-text-secondary hover:text-claude-text p-1.5 rounded hover:bg-gray-100"
                title="Copy answer"
              >
                {copied ? <Check size={16} /> : <Copy size={16} />}
              </button>

              {hasMetadata && message.metadata && (
                <button
                  onClick={() => setShowMetadata(!showMetadata)}
                  className="text-claude-text-secondary hover:text-claude-text text-xs px-2 py-1 rounded hover:bg-gray-100 flex items-center gap-1"
                >
                  <Clock size={14} />
                  {message.metadata?.latency_ms}ms
                  {showMetadata ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                </button>
              )}

              {hasSources && message.sources && (
                <button
                  onClick={() => setShowSources(!showSources)}
                  className="text-claude-text-secondary hover:text-claude-text text-xs px-2 py-1 rounded hover:bg-gray-100 flex items-center gap-1"
                >
                  {message.sources?.length} {message.sources && message.sources.length === 1 ? 'source' : 'sources'}
                  {showSources ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                </button>
              )}
            </div>

            {/* Expanded Metadata */}
            {showMetadata && hasMetadata && message.metadata && (
              <div className="mt-3 pt-3 border-t border-gray-100 space-y-2">
                <div className="flex flex-wrap gap-2 text-xs">
                  <span className="text-claude-text-secondary">
                    Model: <span className="font-medium">{message.metadata?.model_name}</span>
                  </span>
                  <span className="text-gray-400">•</span>
                  <span className="text-claude-text-secondary">
                    Retrieved: <span className="font-medium">{message.metadata?.retrieval_k} docs</span>
                  </span>
                </div>
                {message.metadata?.techniques_used && message.metadata.techniques_used.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {message.metadata.techniques_used.map((technique) => (
                      <span
                        key={technique}
                        className="px-2 py-0.5 bg-claude-user-msg text-claude-text rounded text-xs font-medium"
                      >
                        {technique}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Sources Section */}
          {showSources && hasSources && message.sources && (
            <div className="mt-3 space-y-2">
              {message.sources?.map((source, idx) => (
                <div
                  key={idx}
                  className="bg-claude-bg rounded-xl p-3 border border-claude-border hover:border-gray-300"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs font-semibold text-claude-text-secondary">
                          [{idx + 1}]
                        </span>
                        <h4 className="font-medium text-claude-text text-sm truncate">
                          {source.page_title}
                        </h4>
                      </div>
                      <p className="text-xs text-claude-text-secondary mb-2">
                        {source.notebook_name} → {source.section_name}
                      </p>
                      <p className="text-xs text-claude-text line-clamp-2">
                        {source.content_snippet}
                      </p>
                    </div>
                    {source.url && (
                      <a
                        href={source.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-claude-primary hover:text-claude-primary-hover p-1 flex-shrink-0"
                        title="Open in OneNote"
                      >
                        <ExternalLink size={16} />
                      </a>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    );
  }

  // Brutalist theme
  return (
    <div className="flex items-start gap-4 max-w-3xl animate-fadeInUp">
      <div className="w-12 h-12 bg-neo-pink border-4 border-neo-black shadow-brutal-sm flex items-center justify-center flex-shrink-0 animate-bounce">
        <span className="text-neo-black text-lg font-black">AI</span>
      </div>

      <div className="flex-1 min-w-0">
        <div className="bg-white border-4 border-neo-black shadow-brutal px-5 py-4">
          <div className="prose max-w-none">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                a: ({ node, ...props }) => (
                  <a {...props} target="_blank" rel="noopener noreferrer" className="text-neo-black underline" />
                ),
                code: ({ node, className, children, ...props }) => {
                  const isInline = !className;
                  if (isInline) {
                    return <code className="bg-gray-100 px-1 rounded text-sm" {...props}>{children}</code>;
                  }
                  return (
                    <pre className="rounded bg-gray-100 p-3 overflow-auto text-sm"><code className={className} {...props}>{children}</code></pre>
                  );
                }
              }}
            >
              {message.content}
            </ReactMarkdown>
          </div>

          {/* Action buttons */}
          <div className="flex items-center gap-2 mt-4 pt-4 border-t-4 border-neo-black">
            <button
              onClick={handleCopy}
              className="text-neo-black bg-neo-yellow hover:bg-neo-lime p-2 border-3 border-neo-black shadow-brutal-sm hover:shadow-brutal hover:translate-x-0.5 hover:translate-y-0.5 active:shadow-none active:translate-x-1 active:translate-y-1"
              title="Copy answer"
            >
              {copied ? <Check size={18} strokeWidth={3} /> : <Copy size={18} strokeWidth={3} />}
            </button>

            {hasMetadata && message.metadata && (
              <button
                onClick={() => setShowMetadata(!showMetadata)}
                className="text-neo-black bg-neo-cyan hover:bg-neo-lime text-xs px-3 py-2 border-3 border-neo-black shadow-brutal-sm hover:shadow-brutal hover:translate-x-0.5 hover:translate-y-0.5 active:shadow-none active:translate-x-1 active:translate-y-1 flex items-center gap-1.5 font-black uppercase"
              >
                <Clock size={16} strokeWidth={3} />
                {message.metadata?.latency_ms}ms
                {showMetadata ? <ChevronUp size={16} strokeWidth={3} /> : <ChevronDown size={16} strokeWidth={3} />}
              </button>
            )}

            {hasSources && message.sources && (
              <button
                onClick={() => setShowSources(!showSources)}
                className="text-neo-black bg-neo-orange hover:bg-neo-pink text-xs px-3 py-2 border-3 border-neo-black shadow-brutal-sm hover:shadow-brutal hover:translate-x-0.5 hover:translate-y-0.5 active:shadow-none active:translate-x-1 active:translate-y-1 flex items-center gap-1.5 font-black uppercase"
              >
                {message.sources?.length} SOURCE{message.sources && message.sources.length !== 1 ? 'S' : ''}
                {showSources ? <ChevronUp size={16} strokeWidth={3} /> : <ChevronDown size={16} strokeWidth={3} />}
              </button>
            )}
          </div>

          {/* Expanded Metadata */}
          {showMetadata && hasMetadata && message.metadata && (
            <div className="mt-4 pt-4 border-t-4 border-neo-black space-y-3">
              <div className="flex flex-wrap gap-3 text-sm font-bold">
                <span className="text-neo-black bg-neo-yellow px-2 py-1 border-2 border-neo-black">
                  MODEL: {message.metadata?.model_name.toUpperCase()}
                </span>
                <span className="text-neo-black bg-neo-cyan px-2 py-1 border-2 border-neo-black">
                  DOCS: {message.metadata?.retrieval_k}
                </span>
              </div>
              {message.metadata?.techniques_used && message.metadata.techniques_used.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {message.metadata.techniques_used.map((technique) => (
                    <span
                      key={technique}
                      className="px-2 py-1 bg-neo-lime text-neo-black border-2 border-neo-black text-xs font-black uppercase"
                    >
                      {technique}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Sources Section */}
        {showSources && hasSources && message.sources && (
          <div className="mt-4 space-y-3">
            {message.sources?.map((source, idx) => (
              <div
                key={idx}
                className="bg-neo-lime border-4 border-neo-black shadow-brutal p-4"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-sm font-black text-neo-black bg-neo-yellow px-2 py-1 border-2 border-neo-black">
                        [{idx + 1}]
                      </span>
                      <h4 className="font-black text-neo-black text-sm truncate uppercase">
                        {source.page_title}
                      </h4>
                    </div>
                    <p className="text-xs font-bold text-neo-black mb-2 uppercase">
                      {source.notebook_name} → {source.section_name}
                    </p>
                    <p className="text-sm font-semibold text-neo-black line-clamp-2">
                      {source.content_snippet}
                    </p>
                  </div>
                  {source.url && (
                    <a
                      href={source.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-neo-black bg-neo-cyan border-3 border-neo-black p-2 hover:bg-neo-pink shadow-brutal-sm hover:shadow-brutal hover:translate-x-0.5 hover:translate-y-0.5 flex-shrink-0"
                      title="Open in OneNote"
                    >
                      <ExternalLink size={18} strokeWidth={3} />
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default AssistantMessage;
