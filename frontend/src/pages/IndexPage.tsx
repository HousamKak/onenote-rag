import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {  Database, Trash2, Plus, Loader2, FileText } from 'lucide-react';
import { indexApi, demoApi } from '../api/client';
import { useStore } from '../store/useStore';
import { useTheme } from '../context/ThemeContext';
import ConfirmModal from '../components/ConfirmModal';
import NotificationModal from '../components/NotificationModal';

const IndexPage = () => {
  const { theme } = useTheme();
  const queryClient = useQueryClient();
  const setIndexStats = useStore((state) => state.setIndexStats);
  const [demoTexts, setDemoTexts] = useState(['', '', '']);
  const [showClearModal, setShowClearModal] = useState(false);
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

  const syncMutation = useMutation({
    mutationFn: () => indexApi.sync(undefined, true),
    onSuccess: (response) => {
      queryClient.invalidateQueries({ queryKey: ['indexStats'] });
      refetchStats();
      setNotification({
        show: true,
        title: 'Sync Completed',
        message: response.data?.message || 'Documents synced successfully!',
        variant: 'success',
      });
    },
    onError: (error: any) => {
      setNotification({
        show: true,
        title: 'Sync Failed',
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
        message: data?.message || `Added ${data?.documents_added || 0} documents (${data?.chunks_created || 0} chunks)`,
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

  const containerHeight = theme === 'claude' ? 'h-[calc(100vh-64px)]' : 'h-[calc(100vh-80px)]';

  return (
    <>
      <div className={`${containerHeight} overflow-y-auto`}>
        <div className="max-w-7xl mx-auto p-6">
        {/* Header with Stats */}
        <div className="bg-white rounded-lg shadow-sm p-4 mb-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Database className="text-blue-600" size={28} />
              <div>
                <h2 className="text-lg font-semibold">Vector Database</h2>
                <p className="text-sm text-gray-600">Manage your indexed documents</p>
              </div>
            </div>
            <div className="flex items-center gap-6">
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">{stats?.total_documents || 0}</div>
                <div className="text-xs text-gray-600">Documents</div>
              </div>
              <div className="text-center">
                <div className="text-sm font-medium text-gray-900">{stats?.collection_name || 'N/A'}</div>
                <div className="text-xs text-gray-600">Collection</div>
              </div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          {/* OneNote Sync */}
          <div className="bg-white rounded-lg shadow-sm p-4">
            <div className="flex items-center gap-2 mb-3">
              <Database className="text-blue-600" size={20} />
              <h3 className="font-semibold">OneNote Sync</h3>
            </div>
            <p className="text-sm text-gray-600 mb-3">
              Sync documents from your OneNote notebooks.
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => syncMutation.mutate()}
                disabled={syncMutation.isPending}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 text-sm"
              >
                {syncMutation.isPending ? (
                  <>
                    <Loader2 size={16} className="animate-spin" />
                    Syncing...
                  </>
                ) : (
                  <>
                    <Database size={16} />
                    Sync
                  </>
                )}
              </button>
              <button
                onClick={() => setShowClearModal(true)}
                disabled={clearMutation.isPending}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2 border border-red-300 text-red-600 rounded-lg hover:bg-red-50 disabled:bg-gray-100 text-sm"
              >
                {clearMutation.isPending ? (
                  <>
                    <Loader2 size={16} className="animate-spin" />
                    Clearing...
                  </>
                ) : (
                  <>
                    <Trash2 size={16} />
                    Clear
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Demo Documents */}
          <div className="bg-white rounded-lg shadow-sm p-4">
            <div className="flex items-center gap-2 mb-3">
              <FileText className="text-gray-600" size={20} />
              <h3 className="font-semibold">Add Demo Documents</h3>
            </div>
            <p className="text-sm text-gray-600 mb-3">
              Add sample documents for testing.
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => setDemoTexts([...demoTexts, ''])}
                className="flex items-center gap-2 px-4 py-2 border rounded-lg hover:bg-gray-50 text-sm"
              >
                <Plus size={16} />
                Add Field
              </button>
              <button
                onClick={() => demoMutation.mutate()}
                disabled={demoMutation.isPending || !demoTexts.some((t) => t.trim())}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-400 text-sm"
              >
                {demoMutation.isPending ? (
                  <>
                    <Loader2 size={16} className="animate-spin" />
                    Adding...
                  </>
                ) : (
                  <>
                    <Database size={16} />
                    Add to Index
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Demo Documents Input */}
        {demoTexts.length > 0 && (
          <div className="bg-white rounded-lg shadow-sm p-4 mt-4">
            <h4 className="text-sm font-semibold mb-3">Demo Document Fields</h4>
            <div className="grid grid-cols-2 gap-3">
              {demoTexts.map((text, idx) => (
                <textarea
                  key={idx}
                  value={text}
                  onChange={(e) => {
                    const newTexts = [...demoTexts];
                    newTexts[idx] = e.target.value;
                    setDemoTexts(newTexts);
                  }}
                  placeholder={`Document ${idx + 1} text...`}
                  className="px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none text-sm"
                  rows={2}
                />
              ))}
            </div>
          </div>
        )}
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

export default IndexPage;
