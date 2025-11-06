import { useState,useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Database,
  Trash2,
  Plus,
  Loader2,
  FileText,
  RefreshCw,
  CheckCircle,
  XCircle,
  Clock,
  BookOpen,
  FolderOpen,
  ChevronDown,
  ChevronRight,
  Zap,
  Activity,
  AlertCircle,
} from 'lucide-react';
import { indexApi, demoApi, oneNoteApi } from '../api/client';
import { useStore } from '../store/useStore';
import { useTheme } from '../context/ThemeContext';
import ConfirmModal from '../components/ConfirmModal';
import NotificationModal from '../components/NotificationModal';
import type { Notebook, SyncHistory } from '../types';

const IndexPage = () => {
  const { theme } = useTheme();
  const queryClient = useQueryClient();
  const setIndexStats = useStore((state) => state.setIndexStats);
  const [demoTexts, setDemoTexts] = useState(['', '', '']);
  const [showClearModal, setShowClearModal] = useState(false);
  const [expandedNotebooks, setExpandedNotebooks] = useState<Set<string>>(new Set());
  const [selectedNotebooks, setSelectedNotebooks] = useState<Set<string>>(new Set());
  const [syncHistory, setSyncHistory] = useState<SyncHistory[]>([]);
  const [showAnalytics, setShowAnalytics] = useState(false);
  const [notification, setNotification] = useState<{
    show: boolean;
    title: string;
    message: string;
    variant: 'success' | 'error';
  }>({
    show: false,
    title: '',
    message: '',
    variant: 'success',
  });

  const { data: stats, refetch: refetchStats } = useQuery({
    queryKey: ['indexStats'],
    queryFn: async () => {
      const response = await indexApi.getStats();
      setIndexStats(response.data);
      return response.data;
    },
  });

  const { data: notebooks, isLoading: notebooksLoading, error: notebooksError } = useQuery({
    queryKey: ['notebooks'],
    queryFn: async () => {
      const response = await oneNoteApi.listNotebooks();
      return response.data.notebooks;
    },
    retry: 1,
  });

  const syncMutation = useMutation({
    mutationFn: (selectedIds?: string[]) => indexApi.sync(selectedIds, false),
    onSuccess: (response) => {
      queryClient.invalidateQueries({ queryKey: ['indexStats'] });
      refetchStats();
      const data = response.data;
      const added = data?.documents_added || 0;
      const updated = data?.documents_updated || 0;
      const skipped = data?.documents_skipped || 0;

      // Add to sync history
      const historyEntry: SyncHistory = {
        timestamp: new Date(),
        status: 'success',
        documentsAdded: added,
        documentsUpdated: updated,
        documentsSkipped: skipped,
        chunksCreated: data?.chunks_created || 0,
        message: data?.message || 'Partial sync completed',
      };
      setSyncHistory((prev) => [historyEntry, ...prev].slice(0, 5));

      setNotification({
        show: true,
        title: 'Partial Sync Completed',
        message: data?.message || `Added: ${added}, Updated: ${updated}, Skipped: ${skipped}`,
        variant: 'success',
      });
    },
    onError: (error: any) => {
      const historyEntry: SyncHistory = {
        timestamp: new Date(),
        status: 'error',
        documentsAdded: 0,
        documentsUpdated: 0,
        documentsSkipped: 0,
        chunksCreated: 0,
        message: error.response?.data?.detail || error.message,
      };
      setSyncHistory((prev) => [historyEntry, ...prev].slice(0, 5));

      setNotification({
        show: true,
        title: 'Sync Failed',
        message: error.response?.data?.detail || error.message,
        variant: 'error',
      });
    },
  });

  const fullSyncMutation = useMutation({
    mutationFn: (selectedIds?: string[]) => indexApi.sync(selectedIds, true),
    onSuccess: (response) => {
      queryClient.invalidateQueries({ queryKey: ['indexStats'] });
      refetchStats();
      const data = response.data;
      const added = data?.documents_added || 0;

      // Add to sync history
      const historyEntry: SyncHistory = {
        timestamp: new Date(),
        status: 'success',
        documentsAdded: added,
        documentsUpdated: 0,
        documentsSkipped: 0,
        chunksCreated: data?.chunks_created || 0,
        message: 'Full resync completed - all documents reindexed',
      };
      setSyncHistory((prev) => [historyEntry, ...prev].slice(0, 5));

      setNotification({
        show: true,
        title: 'Full Resync Completed',
        message: `Successfully reindexed ${added} documents (${data?.chunks_created || 0} chunks)`,
        variant: 'success',
      });
    },
    onError: (error: any) => {
      const historyEntry: SyncHistory = {
        timestamp: new Date(),
        status: 'error',
        documentsAdded: 0,
        documentsUpdated: 0,
        documentsSkipped: 0,
        chunksCreated: 0,
        message: error.response?.data?.detail || error.message,
      };
      setSyncHistory((prev) => [historyEntry, ...prev].slice(0, 5));

      setNotification({
        show: true,
        title: 'Full Resync Failed',
        message: error.response?.data?.detail || error.message,
        variant: 'error',
      });
    },
  });

  const clearMutation = useMutation({
    mutationFn: () => indexApi.clear(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['indexStats'] });
      refetchStats();
      setShowClearModal(false);
      setNotification({
        show: true,
        title: 'Index Cleared',
        message: 'All documents have been removed from the vector database.',
        variant: 'success',
      });
    },
    onError: (error: any) => {
      setShowClearModal(false);
      setNotification({
        show: true,
        title: 'Clear Failed',
        message: error.response?.data?.detail || error.message,
        variant: 'error',
      });
    },
  });

  const demoMutation = useMutation({
    mutationFn: () => {
      const texts = demoTexts.filter((t) => t.trim());
      return demoApi.addDocuments(texts);
    },
    onSuccess: (response) => {
      queryClient.invalidateQueries({ queryKey: ['indexStats'] });
      refetchStats();
      setDemoTexts(['', '', '']);
      const data = response.data;
      setNotification({
        show: true,
        title: 'Documents Added',
        message:
          data?.message || `Added ${data?.documents_added || 0} documents (${data?.chunks_created || 0} chunks)`,
        variant: 'success',
      });
    },
    onError: (error: any) => {
      setNotification({
        show: true,
        title: 'Add Failed',
        message: error.response?.data?.detail || error.message,
        variant: 'error',
      });
    },
  });

  const toggleNotebook = (notebookId: string) => {
    const newExpanded = new Set(expandedNotebooks);
    if (newExpanded.has(notebookId)) {
      newExpanded.delete(notebookId);
    } else {
      newExpanded.add(notebookId);
    }
    setExpandedNotebooks(newExpanded);
  };

  const toggleSelectNotebook = (notebookId: string) => {
    const newSelected = new Set(selectedNotebooks);
    if (newSelected.has(notebookId)) {
      newSelected.delete(notebookId);
    } else {
      newSelected.add(notebookId);
    }
    setSelectedNotebooks(newSelected);
  };

  const handleSyncSelected = () => {
    if (selectedNotebooks.size > 0) {
      syncMutation.mutate(Array.from(selectedNotebooks));
    } else {
      syncMutation.mutate(undefined);
    }
  };

  const containerHeight = theme === 'claude' ? 'h-[calc(100vh-64px)]' : 'h-[calc(100vh-80px)]';

  return (
    <>
      <div className={`${containerHeight} overflow-y-auto`}>
        <div className="max-w-7xl mx-auto p-6 space-y-4">
          {/* Header with Enhanced Stats */}
          <div className="bg-white rounded-lg shadow-sm p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <Database className="text-blue-600" size={32} />
                <div>
                  <h2 className="text-2xl font-bold">Data Sources</h2>
                  <p className="text-sm text-gray-600">Manage and sync your knowledge base</p>
                </div>
              </div>
              <div className="flex items-center gap-6">
                <div className="text-center px-4 py-2 bg-blue-50 rounded-lg">
                  <div className="text-3xl font-bold text-blue-600">{stats?.total_documents || 0}</div>
                  <div className="text-xs text-gray-600 font-medium">Documents</div>
                </div>
                <div className="text-center px-4 py-2 bg-green-50 rounded-lg">
                  <div className="flex items-center gap-1 text-sm font-semibold text-green-700">
                    <CheckCircle size={16} />
                    <span>Active</span>
                  </div>
                  <div className="text-xs text-gray-600">{stats?.collection_name || 'N/A'}</div>
                </div>
              </div>
            </div>

            {/* Quick Actions */}
            <div className="flex items-center gap-3 pt-4 border-t">
              <button
                onClick={handleSyncSelected}
                disabled={syncMutation.isPending || fullSyncMutation.isPending}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 text-sm font-medium transition-colors"
              >
                {syncMutation.isPending ? (
                  <>
                    <Loader2 size={16} className="animate-spin" />
                    Syncing...
                  </>
                ) : (
                  <>
                    <RefreshCw size={16} />
                    {selectedNotebooks.size > 0 ? `Sync Selected (${selectedNotebooks.size})` : 'Sync All'}
                  </>
                )}
              </button>
              <button
                onClick={() => {
                  if (selectedNotebooks.size > 0) {
                    fullSyncMutation.mutate(Array.from(selectedNotebooks));
                  } else {
                    fullSyncMutation.mutate(undefined);
                  }
                }}
                disabled={syncMutation.isPending || fullSyncMutation.isPending}
                className="flex items-center gap-2 px-4 py-2 border-2 border-orange-400 text-orange-600 rounded-lg hover:bg-orange-50 disabled:bg-gray-100 text-sm font-medium transition-colors"
              >
                {fullSyncMutation.isPending ? (
                  <>
                    <Loader2 size={16} className="animate-spin" />
                    Resyncing...
                  </>
                ) : (
                  <>
                    <Zap size={16} />
                    Reset & Full Resync
                  </>
                )}
              </button>
              <button
                onClick={() => setShowClearModal(true)}
                disabled={clearMutation.isPending || syncMutation.isPending || fullSyncMutation.isPending}
                className="flex items-center gap-2 px-4 py-2 border-2 border-red-300 text-red-600 rounded-lg hover:bg-red-50 disabled:bg-gray-100 text-sm font-medium transition-colors"
              >
                {clearMutation.isPending ? (
                  <>
                    <Loader2 size={16} className="animate-spin" />
                    Clearing...
                  </>
                ) : (
                  <>
                    <Trash2 size={16} />
                    Clear All
                  </>
                )}
              </button>
              {selectedNotebooks.size > 0 && (
                <button
                  type="button"
                  onClick={() => setSelectedNotebooks(new Set())}
                  className="text-sm text-gray-600 hover:text-gray-900 underline"
                >
                  Clear selection
                </button>
              )}
            </div>
          </div>

          {/* Analytics Dashboard */}
          {showAnalytics && notebooks && notebooks.length > 0 && (
            <div className="bg-white rounded-lg shadow-sm p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <Activity className="text-indigo-600" size={24} />
                  <h3 className="text-lg font-bold">Analytics Overview</h3>
                </div>
                <button
                  type="button"
                  onClick={() => setShowAnalytics(false)}
                  className="text-sm text-gray-500 hover:text-gray-700"
                >
                  Hide
                </button>
              </div>
              <AnalyticsDashboard notebooks={notebooks} />
            </div>
          )}

          {/* Toggle Analytics Button */}
          {notebooks && notebooks.length > 0 && !showAnalytics && (
            <button
              type="button"
              onClick={() => setShowAnalytics(true)}
              className="w-full bg-gradient-to-r from-indigo-50 to-purple-50 border-2 border-indigo-200 rounded-lg p-4 hover:from-indigo-100 hover:to-purple-100 transition-colors"
            >
              <div className="flex items-center justify-center gap-2 text-indigo-700 font-medium">
                <Activity size={20} />
                <span>Show Analytics Dashboard</span>
              </div>
            </button>
          )}

          <div className="grid grid-cols-3 gap-4">
            {/* OneNote Sources - Larger Column */}
            <div className="col-span-2 bg-white rounded-lg shadow-sm overflow-hidden">
              <div className="p-4 border-b bg-gradient-to-r from-blue-50 to-indigo-50">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <BookOpen className="text-blue-600" size={24} />
                    <div>
                      <h3 className="font-bold text-lg">OneNote Notebooks</h3>
                      <p className="text-xs text-gray-600">Browse and select notebooks to sync</p>
                    </div>
                  </div>
                  {notebooks && (
                    <div className="text-sm text-gray-600">
                      {notebooks.length} {notebooks.length === 1 ? 'notebook' : 'notebooks'}
                    </div>
                  )}
                </div>
              </div>

              <div className="max-h-[500px] overflow-y-auto">
                {notebooksLoading && (
                  <div className="flex items-center justify-center p-12">
                    <Loader2 className="animate-spin text-blue-600" size={32} />
                  </div>
                )}

                {notebooksError && (
                  <div className="p-6 text-center">
                    <AlertCircle className="mx-auto mb-3 text-orange-500" size={32} />
                    <p className="text-sm text-gray-600 mb-2">Unable to connect to OneNote</p>
                    <p className="text-xs text-gray-500">Check your authentication settings</p>
                  </div>
                )}

                {notebooks && notebooks.length === 0 && (
                  <div className="p-6 text-center">
                    <BookOpen className="mx-auto mb-3 text-gray-400" size={32} />
                    <p className="text-sm text-gray-600">No notebooks found</p>
                  </div>
                )}

                {notebooks && notebooks.length > 0 && (
                  <div className="divide-y">
                    {notebooks.map((notebook) => (
                      <NotebookItem
                        key={notebook.id}
                        notebook={notebook}
                        isExpanded={expandedNotebooks.has(notebook.id)}
                        isSelected={selectedNotebooks.has(notebook.id)}
                        onToggleExpand={() => toggleNotebook(notebook.id)}
                        onToggleSelect={() => toggleSelectNotebook(notebook.id)}
                      />
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Right Sidebar - Sync History & Demo */}
            <div className="space-y-4">
              {/* Sync History */}
              <div className="bg-white rounded-lg shadow-sm overflow-hidden">
                <div className="p-4 border-b bg-gradient-to-r from-green-50 to-emerald-50">
                  <div className="flex items-center gap-2">
                    <Activity className="text-green-600" size={20} />
                    <h3 className="font-bold text-sm">Recent Syncs</h3>
                  </div>
                </div>
                <div className="max-h-[300px] overflow-y-auto">
                  {syncHistory.length === 0 ? (
                    <div className="p-4 text-center">
                      <Clock className="mx-auto mb-2 text-gray-400" size={24} />
                      <p className="text-xs text-gray-500">No sync history yet</p>
                    </div>
                  ) : (
                    <div className="divide-y">
                      {syncHistory.map((entry, idx) => (
                        <div key={idx} className="p-3 hover:bg-gray-50">
                          <div className="flex items-start gap-2 mb-1">
                            {entry.status === 'success' ? (
                              <CheckCircle size={14} className="text-green-600 mt-0.5 flex-shrink-0" />
                            ) : (
                              <XCircle size={14} className="text-red-600 mt-0.5 flex-shrink-0" />
                            )}
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center justify-between mb-1">
                                <span className="text-xs font-semibold text-gray-900">
                                  {entry.status === 'success' ? 'Success' : 'Failed'}
                                </span>
                                <span className="text-xs text-gray-500">
                                  {new Date(entry.timestamp).toLocaleTimeString()}
                                </span>
                              </div>
                              {entry.status === 'success' && (
                                <div className="text-xs text-gray-600">
                                  <span className="text-green-600 font-medium">+{entry.documentsAdded}</span>
                                  {' / '}
                                  <span className="text-blue-600 font-medium">~{entry.documentsUpdated}</span>
                                  {' / '}
                                  <span className="text-gray-500">-{entry.documentsSkipped}</span>
                                </div>
                              )}
                              <p className="text-xs text-gray-500 truncate mt-1">{entry.message}</p>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Demo Documents */}
              <div className="bg-white rounded-lg shadow-sm overflow-hidden">
                <div className="p-4 border-b bg-gradient-to-r from-purple-50 to-pink-50">
                  <div className="flex items-center gap-2">
                    <FileText className="text-purple-600" size={20} />
                    <div>
                      <h3 className="font-bold text-sm">Quick Test</h3>
                      <p className="text-xs text-gray-600">Add demo documents</p>
                    </div>
                  </div>
                </div>
                <div className="p-4">
                  <div className="space-y-2 mb-3">
                    {demoTexts.map((text, idx) => (
                      <textarea
                        key={idx}
                        value={text}
                        onChange={(e) => {
                          const newTexts = [...demoTexts];
                          newTexts[idx] = e.target.value;
                          setDemoTexts(newTexts);
                        }}
                        placeholder={`Demo doc ${idx + 1}...`}
                        className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent resize-none text-xs"
                        rows={2}
                      />
                    ))}
                  </div>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => setDemoTexts([...demoTexts, ''])}
                      className="flex items-center gap-1 px-3 py-2 border rounded-lg hover:bg-gray-50 text-xs font-medium"
                    >
                      <Plus size={14} />
                      Add
                    </button>
                    <button
                      type="button"
                      onClick={() => demoMutation.mutate()}
                      disabled={demoMutation.isPending || !demoTexts.some((t) => t.trim())}
                      className="flex-1 flex items-center justify-center gap-1 px-3 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:bg-gray-400 text-xs font-medium"
                    >
                      {demoMutation.isPending ? (
                        <>
                          <Loader2 size={14} className="animate-spin" />
                          Adding...
                        </>
                      ) : (
                        <>
                          <Zap size={14} />
                          Index
                        </>
                      )}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Clear Confirmation Modal */}
      <ConfirmModal
        isOpen={showClearModal}
        onClose={() => setShowClearModal(false)}
        onConfirm={() => clearMutation.mutate()}
        title="Clear All Documents"
        message="Are you sure you want to clear all documents from the vector database? This action cannot be undone."
        confirmText="Clear All"
        cancelText="Cancel"
        variant="danger"
      />

      {/* Notification Modal */}
      <NotificationModal
        isOpen={notification.show}
        onClose={() => setNotification({ ...notification, show: false })}
        title={notification.title}
        message={notification.message}
        variant={notification.variant}
      />
    </>
  );
};

// Analytics Dashboard Component
const AnalyticsDashboard = ({ notebooks }: { notebooks: Notebook[] }) => {
  const { data: indexedPages } = useQuery({
    queryKey: ['indexedPages'],
    queryFn: async () => {
      const response = await indexApi.getPages();
      return response.data.pages;
    },
  });

  // Calculate statistics
  const totalNotebooks = notebooks.length;
  const [sectionStats, setSectionStats] = useState<{ total: number; byNotebook: Record<string, number> }>({
    total: 0,
    byNotebook: {},
  });

  // Fetch sections for all notebooks
  const sectionQueries = notebooks.map((notebook) =>
    useQuery({
      queryKey: ['sections', notebook.id],
      queryFn: async () => {
        const response = await oneNoteApi.listSections(notebook.id);
        return { notebookId: notebook.id, sections: response.data.sections };
      },
    })
  );

  // Update section stats when queries complete
  useEffect(() => {
    const allSections = sectionQueries.filter((q) => q.data).map((q) => q.data!);
    const total = allSections.reduce((sum, { sections }) => sum + sections.length, 0);
    const byNotebook: Record<string, number> = {};
    allSections.forEach(({ notebookId, sections }) => {
      byNotebook[notebookId] = sections.length;
    });
    setSectionStats({ total, byNotebook });
  }, [sectionQueries]);

  const totalIndexedPages = indexedPages?.length || 0;
  const totalChunks = indexedPages?.reduce((sum, page) => sum + (page.chunk_count || 0), 0) || 0;

  // Group pages by notebook
  const pagesByNotebook: Record<string, number> = {};
  indexedPages?.forEach((page) => {
    const notebook = page.notebook_name;
    pagesByNotebook[notebook] = (pagesByNotebook[notebook] || 0) + 1;
  });

  // Group pages by section
  const pagesBySection: Record<string, number> = {};
  indexedPages?.forEach((page) => {
    const section = page.section_name;
    pagesBySection[section] = (pagesBySection[section] || 0) + 1;
  });

  // Find most active notebook
  const mostActiveNotebook = Object.entries(pagesByNotebook).sort((a, b) => b[1] - a[1])[0];
  const mostActiveSection = Object.entries(pagesBySection).sort((a, b) => b[1] - a[1])[0];

  // Calculate average chunks per page
  const avgChunksPerPage = totalIndexedPages > 0 ? (totalChunks / totalIndexedPages).toFixed(1) : '0';

  return (
    <div className="space-y-4">
      {/* Key Metrics */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-gradient-to-br from-blue-50 to-blue-100 p-4 rounded-lg border border-blue-200">
          <div className="text-2xl font-bold text-blue-700">{totalNotebooks}</div>
          <div className="text-xs text-blue-600 font-medium">Total Notebooks</div>
        </div>
        <div className="bg-gradient-to-br from-green-50 to-green-100 p-4 rounded-lg border border-green-200">
          <div className="text-2xl font-bold text-green-700">{sectionStats.total}</div>
          <div className="text-xs text-green-600 font-medium">Total Sections</div>
        </div>
        <div className="bg-gradient-to-br from-purple-50 to-purple-100 p-4 rounded-lg border border-purple-200">
          <div className="text-2xl font-bold text-purple-700">{totalIndexedPages}</div>
          <div className="text-xs text-purple-600 font-medium">Indexed Pages</div>
        </div>
        <div className="bg-gradient-to-br from-orange-50 to-orange-100 p-4 rounded-lg border border-orange-200">
          <div className="text-2xl font-bold text-orange-700">{totalChunks}</div>
          <div className="text-xs text-orange-600 font-medium">Total Chunks</div>
        </div>
      </div>

      {/* Detailed Statistics */}
      <div className="grid grid-cols-2 gap-4">
        {/* Pages by Notebook */}
        <div className="bg-gray-50 p-4 rounded-lg border">
          <h4 className="font-semibold text-sm mb-3 text-gray-700">Pages per Notebook</h4>
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {Object.entries(pagesByNotebook)
              .sort((a, b) => b[1] - a[1])
              .map(([notebook, count]) => (
                <div key={notebook} className="flex items-center justify-between">
                  <span className="text-xs text-gray-700 truncate flex-1 mr-2">{notebook}</span>
                  <div className="flex items-center gap-2">
                    <div className="w-24 bg-gray-200 rounded-full h-2">
                      <div
                        className="bg-blue-600 h-2 rounded-full"
                        style={{
                          width: `${(count / Math.max(...Object.values(pagesByNotebook))) * 100}%`,
                        }}
                      />
                    </div>
                    <span className="text-xs font-semibold text-gray-900 w-8 text-right">{count}</span>
                  </div>
                </div>
              ))}
          </div>
        </div>

        {/* Pages by Section */}
        <div className="bg-gray-50 p-4 rounded-lg border">
          <h4 className="font-semibold text-sm mb-3 text-gray-700">Top Sections by Page Count</h4>
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {Object.entries(pagesBySection)
              .sort((a, b) => b[1] - a[1])
              .slice(0, 10)
              .map(([section, count]) => (
                <div key={section} className="flex items-center justify-between">
                  <span className="text-xs text-gray-700 truncate flex-1 mr-2">{section}</span>
                  <div className="flex items-center gap-2">
                    <div className="w-24 bg-gray-200 rounded-full h-2">
                      <div
                        className="bg-green-600 h-2 rounded-full"
                        style={{
                          width: `${(count / Math.max(...Object.values(pagesBySection))) * 100}%`,
                        }}
                      />
                    </div>
                    <span className="text-xs font-semibold text-gray-900 w-8 text-right">{count}</span>
                  </div>
                </div>
              ))}
          </div>
        </div>
      </div>

      {/* Additional Insights */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-indigo-50 p-4 rounded-lg border border-indigo-200">
          <div className="text-xs text-indigo-600 font-medium mb-1">Most Active Notebook</div>
          <div className="text-sm font-semibold text-indigo-900 truncate">
            {mostActiveNotebook ? mostActiveNotebook[0] : 'N/A'}
          </div>
          <div className="text-xs text-indigo-600 mt-1">
            {mostActiveNotebook ? `${mostActiveNotebook[1]} pages` : ''}
          </div>
        </div>
        <div className="bg-teal-50 p-4 rounded-lg border border-teal-200">
          <div className="text-xs text-teal-600 font-medium mb-1">Most Active Section</div>
          <div className="text-sm font-semibold text-teal-900 truncate">
            {mostActiveSection ? mostActiveSection[0] : 'N/A'}
          </div>
          <div className="text-xs text-teal-600 mt-1">
            {mostActiveSection ? `${mostActiveSection[1]} pages` : ''}
          </div>
        </div>
        <div className="bg-amber-50 p-4 rounded-lg border border-amber-200">
          <div className="text-xs text-amber-600 font-medium mb-1">Avg. Chunks per Page</div>
          <div className="text-sm font-semibold text-amber-900">{avgChunksPerPage}</div>
          <div className="text-xs text-amber-600 mt-1">chunks/page ratio</div>
        </div>
      </div>
    </div>
  );
};

// Notebook Item Component
const NotebookItem = ({
  notebook,
  isExpanded,
  isSelected,
  onToggleExpand,
  onToggleSelect,
}: {
  notebook: Notebook;
  isExpanded: boolean;
  isSelected: boolean;
  onToggleExpand: () => void;
  onToggleSelect: () => void;
}) => {
  const { data: sections, isLoading: sectionsLoading } = useQuery({
    queryKey: ['sections', notebook.id],
    queryFn: async () => {
      const response = await oneNoteApi.listSections(notebook.id);
      return response.data.sections;
    },
    enabled: isExpanded,
  });

  return (
    <div className="group">
      <div
        className={`flex items-center gap-3 p-3 hover:bg-gray-50 transition-colors ${
          isSelected ? 'bg-blue-50' : ''
        }`}
      >
        <input
          type="checkbox"
          checked={isSelected}
          onChange={onToggleSelect}
          className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
          aria-label={`Select ${notebook.displayName}`}
        />
        <button type="button" onClick={onToggleExpand} className="flex items-center gap-2 flex-1 text-left">
          {isExpanded ? (
            <ChevronDown size={18} className="text-gray-500 flex-shrink-0" />
          ) : (
            <ChevronRight size={18} className="text-gray-500 flex-shrink-0" />
          )}
          <BookOpen size={18} className="text-blue-600 flex-shrink-0" />
          <div className="flex-1 min-w-0">
            <div className="font-medium text-sm text-gray-900 truncate">{notebook.displayName}</div>
            {notebook.lastModifiedDateTime && (
              <div className="text-xs text-gray-500">
                Modified {new Date(notebook.lastModifiedDateTime).toLocaleDateString()}
              </div>
            )}
          </div>
        </button>
        {sections && (
          <div className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded font-semibold">
            {sections.length} sections
          </div>
        )}
      </div>

      {isExpanded && (
        <div className="bg-gray-50 border-l-4 border-blue-200 ml-4">
          {sectionsLoading && (
            <div className="p-4 flex items-center gap-2 text-sm text-gray-600">
              <Loader2 size={16} className="animate-spin" />
              Loading sections...
            </div>
          )}
          {sections && sections.length === 0 && (
            <div className="p-4 text-sm text-gray-500">No sections found</div>
          )}
          {sections &&
            sections.length > 0 &&
            sections.map((section) => (
              <SectionItem key={section.id} section={section} />
            ))}
        </div>
      )}
    </div>
  );
};

// Section Item Component with Analytics
const SectionItem = ({ section }: { section: any }) => {
  const [showPages, setShowPages] = useState(false);
  const { data: pages, isLoading: pagesLoading } = useQuery({
    queryKey: ['pages', section.id],
    queryFn: async () => {
      const response = await oneNoteApi.listPages(section.id);
      return response.data.pages;
    },
    enabled: showPages,
  });

  return (
    <div className="border-b border-gray-200 last:border-b-0">
      <button
        type="button"
        onClick={() => setShowPages(!showPages)}
        className="w-full flex items-center justify-between p-3 hover:bg-gray-100 transition-colors"
      >
        <div className="flex items-center gap-2 flex-1 min-w-0">
          {showPages ? (
            <ChevronDown size={14} className="text-gray-500 ml-6 flex-shrink-0" />
          ) : (
            <ChevronRight size={14} className="text-gray-500 ml-6 flex-shrink-0" />
          )}
          <FolderOpen size={16} className="text-gray-600 flex-shrink-0" />
          <div className="flex-1 min-w-0">
            <span className="text-sm text-gray-700 font-medium">{section.displayName}</span>
            {section.lastModifiedDateTime && (
              <div className="text-xs text-gray-500">
                Updated {new Date(section.lastModifiedDateTime).toLocaleDateString()}
              </div>
            )}
          </div>
        </div>
        {pages && (
          <div className="flex items-center gap-2 ml-2">
            <div className="text-xs bg-gray-200 text-gray-700 px-2 py-1 rounded font-semibold">
              {pages.length} pages
            </div>
          </div>
        )}
      </button>
      {showPages && (
        <div className="bg-white ml-12 border-l-2 border-gray-300">
          {pagesLoading && (
            <div className="p-3 flex items-center gap-2 text-xs text-gray-600">
              <Loader2 size={14} className="animate-spin" />
              Loading pages...
            </div>
          )}
          {pages && pages.length === 0 && (
            <div className="p-3 text-xs text-gray-500">No pages found</div>
          )}
          {pages &&
            pages.length > 0 &&
            pages.map((page) => (
              <div key={page.id} className="flex items-center justify-between p-2 hover:bg-gray-50 border-b last:border-b-0">
                <div className="flex items-center gap-2 flex-1 min-w-0">
                  <FileText size={14} className="text-gray-500 ml-2 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="text-xs text-gray-700 truncate">{page.title}</div>
                    {page.lastModifiedDateTime && (
                      <div className="text-xs text-gray-400">
                        {new Date(page.lastModifiedDateTime).toLocaleDateString()}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
        </div>
      )}
    </div>
  );
};

export default IndexPage;
