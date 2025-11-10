# Scalable Frontend Architecture
## OneNote RAG Platform - React/TypeScript Implementation

**Version:** 2.0
**Date:** January 2025
**Status:** Architecture Specification for Production Scale

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Architectural Principles](#architectural-principles)
3. [Technology Stack](#technology-stack)
4. [Application Architecture](#application-architecture)
5. [Component Architecture](#component-architecture)
6. [State Management](#state-management)
7. [Feature Implementations](#feature-implementations)
8. [Performance Optimization](#performance-optimization)
9. [Design System](#design-system)
10. [Accessibility](#accessibility)
11. [Testing Strategy](#testing-strategy)
12. [Build & Deployment](#build--deployment)

---

## Executive Summary

This document defines a scalable, maintainable frontend architecture for the OneNote RAG platform, extending the existing React/TypeScript foundation to support advanced features including image management, diagram generation, file selection, and multi-conversation management.

### Key Design Goals

- **Scalability**: Support 10,000+ documents and hundreds of conversations
- **Performance**: <100ms TTI (Time to Interactive), <16ms frame rate
- **Modularity**: Composable components with clear responsibilities
- **Type Safety**: Comprehensive TypeScript coverage
- **Accessibility**: WCAG 2.1 AA compliance
- **Maintainability**: Clear patterns and conventions
- **Extensibility**: Easy to add new features

### Technology Stack (Enhanced)

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Framework** | React 18+ | Component-based UI with Concurrent features |
| **Language** | TypeScript 5+ | Type safety and better DX |
| **Build Tool** | Vite 5+ | Fast dev server and optimized builds |
| **State Management** | Zustand 4+ | Lightweight global state |
| **Server State** | TanStack Query 5+ | Server state caching and synchronization |
| **Routing** | React Router 6+ | Client-side routing |
| **Styling** | Tailwind CSS 3+ | Utility-first CSS framework |
| **UI Components** | Custom + Radix UI | Accessible component primitives |
| **Forms** | React Hook Form | Performant form management |
| **Data Visualization** | Recharts / D3.js | Charts and diagrams |
| **Image Handling** | React Image Gallery | Image viewer and lightbox |
| **Markdown** | React Markdown + Remark | Markdown rendering |
| **Code Highlighting** | Prism.js | Syntax highlighting |
| **Testing** | Vitest + Testing Library | Unit and integration tests |
| **E2E Testing** | Playwright | End-to-end testing |

---

## Architectural Principles

### 1. Component Composition

```
┌──────────────────────────────────────────────────────────┐
│                         App Shell                         │
│                   (Layout, Navigation)                    │
└──────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────┐
│                      Feature Modules                      │
│         (Chat, Browse, Analytics, Settings)              │
└──────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────┐
│                   Domain Components                       │
│    (ConversationList, MessageThread, DocumentGrid)      │
└──────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────┐
│                     UI Components                         │
│           (Button, Input, Modal, Dropdown)               │
└──────────────────────────────────────────────────────────┘
```

### 2. State Management Strategy

```
┌─────────────────────────────────────────────────────────┐
│                    Component State                       │
│              (useState, useReducer)                      │
│                 Ephemeral UI state                       │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                  Zustand Global Store                    │
│          User preferences, UI state, selections          │
│              Persisted to localStorage                   │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                  TanStack Query Cache                    │
│         Server data, optimistic updates, sync            │
│                  Automatic refetching                    │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                      Backend API                         │
│              Source of truth for all data                │
└─────────────────────────────────────────────────────────┘
```

### 3. Code Organization

```
frontend/
├── public/                    # Static assets
├── src/
│   ├── app/                  # App shell and providers
│   │   ├── App.tsx
│   │   ├── Router.tsx
│   │   └── Providers.tsx
│   ├── features/             # Feature modules
│   │   ├── chat/
│   │   ├── browse/
│   │   ├── analytics/
│   │   ├── settings/
│   │   ├── images/           # NEW
│   │   └── diagrams/         # NEW
│   ├── components/           # Shared components
│   │   ├── ui/              # Base UI components
│   │   ├── layout/          # Layout components
│   │   └── domain/          # Domain-specific components
│   ├── hooks/               # Custom hooks
│   │   ├── useQuery.ts
│   │   ├── useAuth.ts
│   │   ├── useImages.ts     # NEW
│   │   └── useDiagrams.ts   # NEW
│   ├── services/            # API clients
│   │   ├── api/
│   │   ├── auth/
│   │   └── websocket/       # NEW
│   ├── store/               # Zustand stores
│   │   ├── useAppStore.ts
│   │   ├── useConversationStore.ts
│   │   ├── useFileSelectionStore.ts  # NEW
│   │   └── useImageStore.ts          # NEW
│   ├── types/               # TypeScript types
│   ├── utils/               # Utility functions
│   ├── styles/              # Global styles
│   └── main.tsx             # Entry point
├── tests/                   # Test files
└── package.json
```

---

## Application Architecture

### App Shell Structure

```typescript
// src/app/App.tsx

import { Providers } from './Providers';
import { Router } from './Router';
import { ErrorBoundary } from '@/components/ErrorBoundary';

export function App() {
  return (
    <ErrorBoundary>
      <Providers>
        <Router />
      </Providers>
    </ErrorBoundary>
  );
}
```

```typescript
// src/app/Providers.tsx

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { AuthProvider } from '@/features/auth/AuthProvider';
import { ThemeProvider } from '@/features/theme/ThemeProvider';
import { ToastProvider } from '@/components/ui/Toast';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      cacheTime: 10 * 60 * 1000, // 10 minutes
      retry: 3,
      refetchOnWindowFocus: false,
    },
  },
});

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <ThemeProvider>
          <ToastProvider>
            {children}
          </ToastProvider>
        </ThemeProvider>
      </AuthProvider>
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  );
}
```

```typescript
// src/app/Router.tsx

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from '@/components/layout/Layout';
import { ProtectedRoute } from '@/features/auth/ProtectedRoute';

// Lazy-loaded routes for code splitting
const ChatPage = lazy(() => import('@/features/chat/ChatPage'));
const BrowsePage = lazy(() => import('@/features/browse/BrowsePage'));
const AnalyticsPage = lazy(() => import('@/features/analytics/AnalyticsPage'));
const SettingsPage = lazy(() => import('@/features/settings/SettingsPage'));
const LoginPage = lazy(() => import('@/features/auth/LoginPage'));

export function Router() {
  return (
    <BrowserRouter>
      <Suspense fallback={<LoadingScreen />}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />

          <Route element={<ProtectedRoute />}>
            <Route element={<Layout />}>
              <Route path="/" element={<Navigate to="/chat" replace />} />
              <Route path="/chat" element={<ChatPage />} />
              <Route path="/chat/:conversationId" element={<ChatPage />} />
              <Route path="/browse" element={<BrowsePage />} />
              <Route path="/analytics" element={<AnalyticsPage />} />
              <Route path="/settings" element={<SettingsPage />} />
            </Route>
          </Route>

          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}
```

---

## Component Architecture

### Feature Module: Chat

```
features/chat/
├── ChatPage.tsx                 # Main page component
├── components/
│   ├── ConversationSidebar/
│   │   ├── index.tsx
│   │   ├── ConversationList.tsx
│   │   ├── ConversationItem.tsx
│   │   └── NewConversationButton.tsx
│   ├── MessageThread/
│   │   ├── index.tsx
│   │   ├── MessageList.tsx
│   │   ├── UserMessage.tsx
│   │   ├── AssistantMessage.tsx
│   │   ├── SystemMessage.tsx
│   │   └── TypingIndicator.tsx
│   ├── MessageInput/
│   │   ├── index.tsx
│   │   ├── TextArea.tsx
│   │   ├── FileAttachment.tsx       # NEW
│   │   └── ContextSelector.tsx      # NEW
│   ├── MessageContent/
│   │   ├── MarkdownRenderer.tsx
│   │   ├── CodeBlock.tsx
│   │   ├── ImageGallery.tsx         # NEW
│   │   ├── DiagramViewer.tsx        # NEW
│   │   └── SourceList.tsx
│   └── ContextPanel/                # NEW
│       ├── index.tsx
│       ├── SelectedFiles.tsx
│       ├── ActiveFilters.tsx
│       └── RAGSettings.tsx
├── hooks/
│   ├── useConversation.ts
│   ├── useMessages.ts
│   ├── useSendMessage.ts
│   └── useStreamingResponse.ts      # NEW
└── types.ts
```

### Key Component Implementations

#### 1. Enhanced Message Input with File Selection

```typescript
// features/chat/components/MessageInput/index.tsx

import { useState, useRef } from 'react';
import { useFileSelectionStore } from '@/store/useFileSelectionStore';
import { ContextSelector } from './ContextSelector';
import { FileAttachment } from './FileAttachment';

interface MessageInputProps {
  conversationId: string;
  onSend: (message: string) => void;
  isLoading: boolean;
}

export function MessageInput({ conversationId, onSend, isLoading }: MessageInputProps) {
  const [message, setMessage] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const selectedFiles = useFileSelectionStore(state => state.selectedFiles);
  const [showContextSelector, setShowContextSelector] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!message.trim() || isLoading) return;

    onSend(message);
    setMessage('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="relative">
      {/* Context selector overlay */}
      {showContextSelector && (
        <ContextSelector
          onClose={() => setShowContextSelector(false)}
          conversationId={conversationId}
        />
      )}

      {/* Selected files badges */}
      {selectedFiles.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-2 px-4">
          {selectedFiles.map(file => (
            <FileAttachment
              key={file.id}
              file={file}
              onRemove={() => useFileSelectionStore.getState().removeFile(file.id)}
            />
          ))}
        </div>
      )}

      <div className="flex items-end gap-2 px-4 py-3">
        <button
          type="button"
          onClick={() => setShowContextSelector(true)}
          className="btn-icon"
          title="Select context files"
        >
          <FileIcon className="w-5 h-5" />
        </button>

        <textarea
          ref={textareaRef}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a question..."
          className="flex-1 resize-none min-h-[44px] max-h-[200px]"
          rows={1}
        />

        <button
          type="submit"
          disabled={!message.trim() || isLoading}
          className="btn-primary"
        >
          <SendIcon className="w-5 h-5" />
        </button>
      </div>
    </form>
  );
}
```

#### 2. Context Selector Component (NEW)

```typescript
// features/chat/components/MessageInput/ContextSelector.tsx

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/services/api';
import { useFileSelectionStore } from '@/store/useFileSelectionStore';
import { Modal } from '@/components/ui/Modal';
import { SearchInput } from '@/components/ui/SearchInput';
import { Checkbox } from '@/components/ui/Checkbox';

interface ContextSelectorProps {
  onClose: () => void;
  conversationId: string;
}

export function ContextSelector({ onClose, conversationId }: ContextSelectorProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const { selectedFiles, toggleFile } = useFileSelectionStore();

  // Fetch available documents
  const { data: documents, isLoading } = useQuery({
    queryKey: ['documents', searchQuery],
    queryFn: () => api.documents.search({ query: searchQuery, limit: 100 }),
  });

  // Group documents by source
  const groupedDocuments = documents?.reduce((acc, doc) => {
    const source = doc.metadata.notebook_name || 'Other';
    if (!acc[source]) acc[source] = [];
    acc[source].push(doc);
    return acc;
  }, {} as Record<string, typeof documents>);

  return (
    <Modal
      isOpen={true}
      onClose={onClose}
      title="Select Context Files"
      size="lg"
    >
      <div className="space-y-4">
        {/* Search */}
        <SearchInput
          value={searchQuery}
          onChange={setSearchQuery}
          placeholder="Search documents..."
        />

        {/* Selected count */}
        <div className="text-sm text-gray-600">
          {selectedFiles.length} files selected
        </div>

        {/* Document tree */}
        <div className="max-h-[500px] overflow-y-auto space-y-4">
          {isLoading ? (
            <LoadingSpinner />
          ) : (
            Object.entries(groupedDocuments || {}).map(([source, docs]) => (
              <div key={source}>
                <h3 className="font-semibold mb-2">{source}</h3>
                <div className="space-y-1">
                  {docs.map(doc => (
                    <label
                      key={doc.id}
                      className="flex items-center gap-2 p-2 hover:bg-gray-50 rounded cursor-pointer"
                    >
                      <Checkbox
                        checked={selectedFiles.some(f => f.id === doc.id)}
                        onChange={() => toggleFile(doc)}
                      />
                      <div className="flex-1">
                        <div className="font-medium">{doc.title}</div>
                        <div className="text-sm text-gray-500">
                          {doc.metadata.section_name}
                        </div>
                      </div>
                    </label>
                  ))}
                </div>
              </div>
            ))
          )}
        </div>

        {/* Actions */}
        <div className="flex justify-end gap-2">
          <button onClick={onClose} className="btn-secondary">
            Cancel
          </button>
          <button onClick={onClose} className="btn-primary">
            Apply Selection
          </button>
        </div>
      </div>
    </Modal>
  );
}
```

#### 3. Enhanced Assistant Message with Images and Diagrams

```typescript
// features/chat/components/MessageThread/AssistantMessage.tsx

import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { ImageGallery } from '../MessageContent/ImageGallery';
import { DiagramViewer } from '../MessageContent/DiagramViewer';
import { SourceList } from '../MessageContent/SourceList';
import { CodeBlock } from '../MessageContent/CodeBlock';

interface AssistantMessageProps {
  message: Message;
}

export function AssistantMessage({ message }: AssistantMessageProps) {
  const [showSources, setShowSources] = useState(false);
  const [showMetadata, setShowMetadata] = useState(false);

  const { content, metadata } = message;
  const sources = metadata?.sources || [];
  const images = metadata?.images || [];
  const diagrams = metadata?.suggested_diagrams || [];

  return (
    <div className="flex gap-4 mb-6">
      {/* Avatar */}
      <div className="w-10 h-10 rounded-full bg-primary flex items-center justify-center">
        <BotIcon className="w-6 h-6 text-white" />
      </div>

      <div className="flex-1 space-y-4">
        {/* Message content */}
        <div className="prose prose-sm max-w-none">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              code: ({ node, inline, className, children, ...props }) => {
                if (inline) {
                  return <code className={className} {...props}>{children}</code>;
                }
                const match = /language-(\w+)/.exec(className || '');
                return (
                  <CodeBlock
                    language={match?.[1] || 'text'}
                    code={String(children).replace(/\n$/, '')}
                  />
                );
              },
            }}
          >
            {content}
          </ReactMarkdown>
        </div>

        {/* Images */}
        {images.length > 0 && (
          <ImageGallery images={images} />
        )}

        {/* Suggested diagrams */}
        {diagrams.length > 0 && (
          <div className="space-y-2">
            <h4 className="text-sm font-semibold">Suggested Visualizations</h4>
            <div className="grid grid-cols-2 gap-2">
              {diagrams.map((diagram, index) => (
                <DiagramViewer
                  key={index}
                  diagram={diagram}
                  onGenerate={() => handleGenerateDiagram(diagram)}
                />
              ))}
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center gap-4 text-sm">
          <button
            onClick={() => navigator.clipboard.writeText(content)}
            className="text-gray-600 hover:text-gray-900"
          >
            <CopyIcon className="w-4 h-4 inline mr-1" />
            Copy
          </button>

          {sources.length > 0 && (
            <button
              onClick={() => setShowSources(!showSources)}
              className="text-gray-600 hover:text-gray-900"
            >
              <DocumentIcon className="w-4 h-4 inline mr-1" />
              {sources.length} sources
            </button>
          )}

          <button
            onClick={() => setShowMetadata(!showMetadata)}
            className="text-gray-600 hover:text-gray-900"
          >
            <InfoIcon className="w-4 h-4 inline mr-1" />
            Details
          </button>
        </div>

        {/* Sources (collapsible) */}
        {showSources && <SourceList sources={sources} />}

        {/* Metadata (collapsible) */}
        {showMetadata && (
          <div className="text-xs text-gray-500 space-y-1">
            <div>Model: {metadata?.model_name}</div>
            <div>Latency: {metadata?.latency_ms}ms</div>
            <div>Tokens: {metadata?.tokens_used}</div>
            <div>Techniques: {metadata?.techniques_used?.join(', ')}</div>
          </div>
        )}
      </div>
    </div>
  );
}
```

#### 4. Image Gallery Component (NEW)

```typescript
// features/chat/components/MessageContent/ImageGallery.tsx

import { useState } from 'react';
import ImageGalleryLib from 'react-image-gallery';
import { Modal } from '@/components/ui/Modal';
import 'react-image-gallery/styles/css/image-gallery.css';

interface Image {
  id: string;
  url: string;
  thumbnail_url: string;
  caption?: string;
  ocr_text?: string;
}

interface ImageGalleryProps {
  images: Image[];
}

export function ImageGallery({ images }: ImageGalleryProps) {
  const [selectedImageIndex, setSelectedImageIndex] = useState<number | null>(null);
  const [showOCR, setShowOCR] = useState(false);

  const galleryImages = images.map(img => ({
    original: img.url,
    thumbnail: img.thumbnail_url,
    description: img.caption,
  }));

  return (
    <div>
      {/* Thumbnail grid */}
      <div className="grid grid-cols-4 gap-2">
        {images.map((image, index) => (
          <div
            key={image.id}
            className="relative aspect-square cursor-pointer group"
            onClick={() => setSelectedImageIndex(index)}
          >
            <img
              src={image.thumbnail_url}
              alt={image.caption || `Image ${index + 1}`}
              className="w-full h-full object-cover rounded"
            />
            <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-30 transition-all rounded flex items-center justify-center">
              <SearchIcon className="w-6 h-6 text-white opacity-0 group-hover:opacity-100" />
            </div>
          </div>
        ))}
      </div>

      {/* Lightbox modal */}
      {selectedImageIndex !== null && (
        <Modal
          isOpen={true}
          onClose={() => setSelectedImageIndex(null)}
          title={images[selectedImageIndex].caption || 'Image'}
          size="xl"
        >
          <div className="space-y-4">
            <ImageGalleryLib
              items={galleryImages}
              startIndex={selectedImageIndex}
              showPlayButton={false}
              showFullscreenButton={true}
            />

            {/* OCR text toggle */}
            {images[selectedImageIndex].ocr_text && (
              <>
                <button
                  onClick={() => setShowOCR(!showOCR)}
                  className="btn-secondary w-full"
                >
                  {showOCR ? 'Hide' : 'Show'} Extracted Text
                </button>

                {showOCR && (
                  <div className="p-4 bg-gray-50 rounded max-h-60 overflow-y-auto">
                    <pre className="text-sm whitespace-pre-wrap">
                      {images[selectedImageIndex].ocr_text}
                    </pre>
                  </div>
                )}
              </>
            )}
          </div>
        </Modal>
      )}
    </div>
  );
}
```

#### 5. Diagram Viewer Component (NEW)

```typescript
// features/chat/components/MessageContent/DiagramViewer.tsx

import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { api } from '@/services/api';
import { Modal } from '@/components/ui/Modal';

interface DiagramSuggestion {
  type: 'flowchart' | 'sequence' | 'mindmap' | 'chart';
  title: string;
  description: string;
  data?: any;
}

interface DiagramViewerProps {
  diagram: DiagramSuggestion;
  onGenerate: () => void;
}

export function DiagramViewer({ diagram, onGenerate }: DiagramViewerProps) {
  const [showModal, setShowModal] = useState(false);
  const [generatedDiagram, setGeneratedDiagram] = useState<any>(null);

  const generateMutation = useMutation({
    mutationFn: (data: DiagramSuggestion) =>
      api.diagrams.generate(data),
    onSuccess: (result) => {
      setGeneratedDiagram(result);
      setShowModal(true);
    },
  });

  const handleGenerate = () => {
    generateMutation.mutate(diagram);
    onGenerate();
  };

  return (
    <>
      <div
        className="border rounded p-4 cursor-pointer hover:border-primary transition-colors"
        onClick={handleGenerate}
      >
        <div className="flex items-center gap-2 mb-2">
          {getIconForType(diagram.type)}
          <h5 className="font-semibold">{diagram.title}</h5>
        </div>
        <p className="text-sm text-gray-600">{diagram.description}</p>
        {generateMutation.isPending && (
          <div className="mt-2">
            <LoadingSpinner size="sm" />
          </div>
        )}
      </div>

      {/* Generated diagram modal */}
      {showModal && generatedDiagram && (
        <Modal
          isOpen={true}
          onClose={() => setShowModal(false)}
          title={diagram.title}
          size="xl"
        >
          <div className="space-y-4">
            <img
              src={generatedDiagram.url}
              alt={diagram.title}
              className="w-full rounded"
            />

            <div className="flex gap-2">
              <button
                onClick={() => downloadImage(generatedDiagram.url, diagram.title)}
                className="btn-secondary"
              >
                <DownloadIcon className="w-4 h-4 mr-2" />
                Download
              </button>
              <button
                onClick={() => copyToClipboard(generatedDiagram.url)}
                className="btn-secondary"
              >
                <CopyIcon className="w-4 h-4 mr-2" />
                Copy Link
              </button>
            </div>
          </div>
        </Modal>
      )}
    </>
  );
}

function getIconForType(type: string) {
  switch (type) {
    case 'flowchart':
      return <WorkflowIcon className="w-5 h-5" />;
    case 'sequence':
      return <TimelineIcon className="w-5 h-5" />;
    case 'mindmap':
      return <NetworkIcon className="w-5 h-5" />;
    case 'chart':
      return <ChartIcon className="w-5 h-5" />;
    default:
      return <FileIcon className="w-5 h-5" />;
  }
}
```

---

## State Management

### Zustand Stores

#### 1. File Selection Store (NEW)

```typescript
// src/store/useFileSelectionStore.ts

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface SelectedFile {
  id: string;
  title: string;
  source_type: string;
  metadata: Record<string, any>;
}

interface FileSelectionStore {
  selectedFiles: SelectedFile[];
  toggleFile: (file: SelectedFile) => void;
  clearSelection: () => void;
  removeFile: (fileId: string) => void;
  selectAll: (files: SelectedFile[]) => void;
}

export const useFileSelectionStore = create<FileSelectionStore>()(
  persist(
    (set, get) => ({
      selectedFiles: [],

      toggleFile: (file) => {
        const { selectedFiles } = get();
        const exists = selectedFiles.find(f => f.id === file.id);

        if (exists) {
          set({ selectedFiles: selectedFiles.filter(f => f.id !== file.id) });
        } else {
          set({ selectedFiles: [...selectedFiles, file] });
        }
      },

      clearSelection: () => set({ selectedFiles: [] }),

      removeFile: (fileId) => {
        const { selectedFiles } = get();
        set({ selectedFiles: selectedFiles.filter(f => f.id !== fileId) });
      },

      selectAll: (files) => set({ selectedFiles: files }),
    }),
    {
      name: 'file-selection-storage',
    }
  )
);
```

#### 2. Image Store (NEW)

```typescript
// src/store/useImageStore.ts

import { create } from 'zustand';

interface ImageCache {
  [imageId: string]: {
    url: string;
    thumbnail_url: string;
    ocr_text?: string;
    caption?: string;
    loading: boolean;
  };
}

interface ImageStore {
  cache: ImageCache;
  addImage: (imageId: string, data: any) => void;
  getImage: (imageId: string) => any;
  clearCache: () => void;
}

export const useImageStore = create<ImageStore>((set, get) => ({
  cache: {},

  addImage: (imageId, data) => {
    set(state => ({
      cache: {
        ...state.cache,
        [imageId]: { ...data, loading: false },
      },
    }));
  },

  getImage: (imageId) => get().cache[imageId],

  clearCache: () => set({ cache: {} }),
}));
```

### TanStack Query Hooks

```typescript
// src/hooks/useConversation.ts

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/services/api';

export function useConversation(conversationId?: string) {
  const queryClient = useQueryClient();

  // Fetch conversation
  const conversation = useQuery({
    queryKey: ['conversation', conversationId],
    queryFn: () => api.conversations.get(conversationId!),
    enabled: !!conversationId,
  });

  // Send message
  const sendMessage = useMutation({
    mutationFn: (message: string) =>
      api.query({
        question: message,
        conversation_id: conversationId,
      }),
    onSuccess: (response) => {
      // Optimistically update conversation
      queryClient.setQueryData(
        ['conversation', conversationId],
        (old: any) => ({
          ...old,
          messages: [
            ...old.messages,
            { role: 'user', content: message },
            { role: 'assistant', content: response.answer, metadata: response.metadata },
          ],
        })
      );
    },
  });

  // Delete conversation
  const deleteConversation = useMutation({
    mutationFn: () => api.conversations.delete(conversationId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
    },
  });

  return {
    conversation: conversation.data,
    isLoading: conversation.isLoading,
    sendMessage,
    deleteConversation,
  };
}
```

```typescript
// src/hooks/useImages.ts (NEW)

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/services/api';

export function useImages(documentId: string) {
  const queryClient = useQueryClient();

  // Fetch images for document
  const images = useQuery({
    queryKey: ['images', documentId],
    queryFn: () => api.images.list(documentId),
  });

  // Upload image
  const uploadImage = useMutation({
    mutationFn: (file: File) => api.images.upload(file, documentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['images', documentId] });
    },
  });

  // Search by image
  const searchByImage = useMutation({
    mutationFn: (file: File) => api.images.search(file),
  });

  return {
    images: images.data || [],
    isLoading: images.isLoading,
    uploadImage,
    searchByImage,
  };
}
```

---

## Performance Optimization

### 1. Code Splitting

```typescript
// Dynamic imports for routes
const ChatPage = lazy(() => import('@/features/chat/ChatPage'));
const BrowsePage = lazy(() => import('@/features/browse/BrowsePage'));

// Dynamic imports for heavy components
const ImageGallery = lazy(() => import('@/components/ImageGallery'));
const DiagramViewer = lazy(() => import('@/components/DiagramViewer'));

// Usage with Suspense
<Suspense fallback={<LoadingSpinner />}>
  <ImageGallery images={images} />
</Suspense>
```

### 2. Virtual Scrolling for Large Lists

```typescript
// features/browse/DocumentList.tsx

import { useVirtualizer } from '@tanstack/react-virtual';

export function DocumentList({ documents }: { documents: Document[] }) {
  const parentRef = useRef<HTMLDivElement>(null);

  const virtualizer = useVirtualizer({
    count: documents.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 80,
    overscan: 5,
  });

  return (
    <div ref={parentRef} className="h-full overflow-auto">
      <div
        style={{
          height: `${virtualizer.getTotalSize()}px`,
          position: 'relative',
        }}
      >
        {virtualizer.getVirtualItems().map((virtualItem) => (
          <div
            key={virtualItem.key}
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: `${virtualItem.size}px`,
              transform: `translateY(${virtualItem.start}px)`,
            }}
          >
            <DocumentItem document={documents[virtualItem.index]} />
          </div>
        ))}
      </div>
    </div>
  );
}
```

### 3. Image Lazy Loading and Optimization

```typescript
// components/ui/OptimizedImage.tsx

interface OptimizedImageProps {
  src: string;
  alt: string;
  width?: number;
  height?: number;
  className?: string;
}

export function OptimizedImage({ src, alt, width, height, className }: OptimizedImageProps) {
  const [isLoaded, setIsLoaded] = useState(false);
  const [error, setError] = useState(false);

  return (
    <div className={`relative ${className}`}>
      {!isLoaded && !error && (
        <div className="absolute inset-0 bg-gray-200 animate-pulse" />
      )}

      <img
        src={src}
        alt={alt}
        width={width}
        height={height}
        loading="lazy"
        onLoad={() => setIsLoaded(true)}
        onError={() => setError(true)}
        className={`transition-opacity duration-300 ${
          isLoaded ? 'opacity-100' : 'opacity-0'
        }`}
      />

      {error && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-100">
          <ImageOffIcon className="w-8 h-8 text-gray-400" />
        </div>
      )}
    </div>
  );
}
```

### 4. Debouncing and Throttling

```typescript
// hooks/useDebounce.ts

import { useEffect, useState } from 'react';

export function useDebounce<T>(value: T, delay: number = 500): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => clearTimeout(timer);
  }, [value, delay]);

  return debouncedValue;
}

// Usage
const [searchQuery, setSearchQuery] = useState('');
const debouncedQuery = useDebounce(searchQuery, 300);

useEffect(() => {
  if (debouncedQuery) {
    // Perform search
  }
}, [debouncedQuery]);
```

### 5. Memoization

```typescript
import { useMemo, useCallback } from 'react';

function ExpensiveComponent({ data }: { data: any[] }) {
  // Memoize expensive calculations
  const processedData = useMemo(() => {
    return data.map(item => expensiveTransformation(item));
  }, [data]);

  // Memoize callbacks
  const handleClick = useCallback((id: string) => {
    // Handle click
  }, []);

  return (
    <div>
      {processedData.map(item => (
        <Item key={item.id} data={item} onClick={handleClick} />
      ))}
    </div>
  );
}

// Memoize component to prevent unnecessary re-renders
export default memo(ExpensiveComponent);
```

---

## Design System

### Tailwind Configuration

```typescript
// tailwind.config.js

export default {
  content: ['./src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#f0f9ff',
          100: '#e0f2fe',
          // ... rest of scale
          600: '#0284c7',
          700: '#0369a1',
        },
        // Custom color schemes for themes
        claude: {
          bg: '#f8fafc',
          surface: '#ffffff',
          border: '#e2e8f0',
          text: '#1e293b',
        },
        brutalist: {
          bg: '#fffbf0',
          surface: '#ffffff',
          border: '#000000',
          text: '#000000',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      spacing: {
        '18': '4.5rem',
        '88': '22rem',
      },
      animation: {
        'fade-in': 'fadeIn 0.2s ease-in',
        'slide-up': 'slideUp 0.3s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
      },
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
    require('@tailwindcss/forms'),
  ],
};
```

### Component Library

Build a consistent component library using Radix UI primitives:

```typescript
// components/ui/Button.tsx

import { forwardRef } from 'react';
import { cva, type VariantProps } from 'class-variance-authority';

const buttonVariants = cva(
  'inline-flex items-center justify-center rounded-md font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 disabled:opacity-50 disabled:pointer-events-none',
  {
    variants: {
      variant: {
        primary: 'bg-primary-600 text-white hover:bg-primary-700',
        secondary: 'bg-gray-200 text-gray-900 hover:bg-gray-300',
        outline: 'border border-gray-300 hover:bg-gray-50',
        ghost: 'hover:bg-gray-100',
        danger: 'bg-red-600 text-white hover:bg-red-700',
      },
      size: {
        sm: 'h-8 px-3 text-sm',
        md: 'h-10 px-4',
        lg: 'h-12 px-6 text-lg',
      },
    },
    defaultVariants: {
      variant: 'primary',
      size: 'md',
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => {
    return (
      <button
        className={buttonVariants({ variant, size, className })}
        ref={ref}
        {...props}
      />
    );
  }
);
```

---

## Accessibility

### WCAG 2.1 AA Compliance

1. **Keyboard Navigation**: All interactive elements accessible via keyboard
2. **Screen Reader Support**: Proper ARIA labels and landmarks
3. **Color Contrast**: Minimum 4.5:1 ratio for text
4. **Focus Indicators**: Visible focus states
5. **Semantic HTML**: Proper heading hierarchy and landmark regions

### Implementation Examples

```typescript
// Accessible modal
<Modal
  isOpen={isOpen}
  onClose={onClose}
  aria-labelledby="modal-title"
  aria-describedby="modal-description"
>
  <h2 id="modal-title">Modal Title</h2>
  <p id="modal-description">Modal description...</p>
</Modal>

// Accessible form
<form onSubmit={handleSubmit} aria-label="Search documents">
  <label htmlFor="search-input" className="sr-only">
    Search query
  </label>
  <input
    id="search-input"
    type="text"
    aria-invalid={!!error}
    aria-describedby={error ? 'search-error' : undefined}
  />
  {error && (
    <div id="search-error" role="alert" className="text-red-600">
      {error}
    </div>
  )}
</form>

// Skip to content link
<a
  href="#main-content"
  className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4"
>
  Skip to main content
</a>
```

---

## Testing Strategy

### Unit Tests (Vitest + Testing Library)

```typescript
// features/chat/components/MessageInput.test.tsx

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MessageInput } from './MessageInput';

describe('MessageInput', () => {
  it('should send message on Enter key', async () => {
    const onSend = vi.fn();

    render(
      <MessageInput
        conversationId="123"
        onSend={onSend}
        isLoading={false}
      />
    );

    const textarea = screen.getByPlaceholderText('Ask a question...');

    fireEvent.change(textarea, { target: { value: 'Test message' } });
    fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: false });

    await waitFor(() => {
      expect(onSend).toHaveBeenCalledWith('Test message');
    });
  });

  it('should not send empty message', () => {
    const onSend = vi.fn();

    render(
      <MessageInput
        conversationId="123"
        onSend={onSend}
        isLoading={false}
      />
    );

    const form = screen.getByRole('form');
    fireEvent.submit(form);

    expect(onSend).not.toHaveBeenCalled();
  });
});
```

### Integration Tests

```typescript
// features/chat/ChatPage.integration.test.tsx

import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ChatPage } from './ChatPage';
import { mockServer } from '@/tests/mocks/server';

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

function renderWithProviders(ui: React.ReactElement) {
  return render(
    <QueryClientProvider client={queryClient}>
      {ui}
    </QueryClientProvider>
  );
}

describe('ChatPage', () => {
  beforeAll(() => mockServer.listen());
  afterEach(() => mockServer.resetHandlers());
  afterAll(() => mockServer.close());

  it('should load conversation history', async () => {
    renderWithProviders(<ChatPage />);

    await waitFor(() => {
      expect(screen.getByText('Welcome message')).toBeInTheDocument();
    });
  });
});
```

### E2E Tests (Playwright)

```typescript
// e2e/chat.spec.ts

import { test, expect } from '@playwright/test';

test.describe('Chat Flow', () => {
  test('should send message and receive response', async ({ page }) => {
    await page.goto('http://localhost:5173/chat');

    // Type message
    await page.fill('[placeholder="Ask a question..."]', 'What is RAG?');

    // Send message
    await page.click('button[type="submit"]');

    // Wait for response
    await expect(page.locator('.assistant-message')).toBeVisible();

    // Verify response contains expected text
    await expect(page.locator('.assistant-message')).toContainText('Retrieval');
  });

  test('should select context files', async ({ page }) => {
    await page.goto('http://localhost:5173/chat');

    // Open context selector
    await page.click('button[title="Select context files"]');

    // Wait for modal
    await expect(page.locator('[role="dialog"]')).toBeVisible();

    // Select a file
    await page.check('input[type="checkbox"]').first();

    // Close modal
    await page.click('button:has-text("Apply Selection")');

    // Verify file badge appears
    await expect(page.locator('.file-attachment')).toBeVisible();
  });
});
```

---

## Build & Deployment

### Vite Configuration

```typescript
// vite.config.ts

import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  build: {
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks: {
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
          'query-vendor': ['@tanstack/react-query'],
          'ui-vendor': ['@radix-ui/react-dialog', '@radix-ui/react-dropdown-menu'],
        },
      },
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
```

### Docker Configuration

```dockerfile
# Dockerfile

# Build stage
FROM node:20-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

### CI/CD Pipeline

```yaml
# .github/workflows/frontend.yml

name: Frontend CI/CD

on:
  push:
    branches: [main, develop]
    paths:
      - 'frontend/**'
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Lint
        run: npm run lint

      - name: Type check
        run: npm run type-check

      - name: Unit tests
        run: npm run test:unit

      - name: Build
        run: npm run build

  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Install dependencies
        run: npm ci

      - name: Install Playwright
        run: npx playwright install --with-deps

      - name: Run E2E tests
        run: npm run test:e2e

  deploy:
    needs: [test, e2e]
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build and push Docker image
        run: |
          docker build -t registry.example.com/onenote-rag-frontend:latest .
          docker push registry.example.com/onenote-rag-frontend:latest

      - name: Deploy to production
        run: |
          # Deploy to Kubernetes/Cloud provider
```

---

## Summary

This scalable frontend architecture provides:

1. **Modern Stack**: React 18, TypeScript, Vite, Tailwind
2. **Advanced Features**: Images, diagrams, file selection, conversations
3. **Performance**: Code splitting, virtualization, lazy loading, caching
4. **Type Safety**: Comprehensive TypeScript coverage
5. **Testing**: Unit, integration, E2E test strategies
6. **Accessibility**: WCAG 2.1 AA compliance
7. **Design System**: Consistent, themed UI components
8. **CI/CD**: Automated testing and deployment

The architecture supports thousands of documents, hundreds of conversations, and provides excellent user experience with <100ms TTI.
