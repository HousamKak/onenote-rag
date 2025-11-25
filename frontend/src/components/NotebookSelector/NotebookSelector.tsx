import React, { useState, useEffect } from 'react';
import type { Notebook } from '../../types';
import { notebookApi } from '../../api/client';
import { NotebookList } from './NotebookList';

interface NotebookSelectorProps {
  onClose: () => void;
  onNotebooksSelected?: (notebookIds: string[]) => Promise<void>;
}

export const NotebookSelector: React.FC<NotebookSelectorProps> = ({
  onClose,
  onNotebooksSelected,
}) => {
  const [notebooks, setNotebooks] = useState<Notebook[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchDiscoveredNotebooks();
  }, []);

  const fetchDiscoveredNotebooks = async () => {
    try {
      setLoading(true);
      setError(null);

      // Discover notebooks from all sources
      const response = await notebookApi.discover();
      const discoveredNotebooks = response.data.notebooks;

      setNotebooks(discoveredNotebooks);

      // Pre-select currently selected notebooks
      const currentlySelected = discoveredNotebooks
        .filter((nb) => nb.isSelected)
        .map((nb) => nb.id);
      setSelectedIds(new Set(currentlySelected));
    } catch (err: any) {
      console.error('Error discovering notebooks:', err);
      setError(err.response?.data?.detail || 'Failed to discover notebooks');
    } finally {
      setLoading(false);
    }
  };

  const toggleNotebook = (id: string) => {
    setSelectedIds((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(id)) {
        newSet.delete(id);
      } else {
        newSet.add(id);
      }
      return newSet;
    });
  };

  const handleSyncSelected = async () => {
    try {
      setSaving(true);
      setError(null);

      const selectedNotebookIds = Array.from(selectedIds);

      // Update selection in backend
      await notebookApi.select(selectedNotebookIds);

      // Call optional callback
      if (onNotebooksSelected) {
        await onNotebooksSelected(selectedNotebookIds);
      }

      // Close dialog
      onClose();
    } catch (err: any) {
      console.error('Error saving selection:', err);
      setError(err.response?.data?.detail || 'Failed to save selection');
      setSaving(false);
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.5)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
      }}
      onClick={onClose}
    >
      <div
        style={{
          backgroundColor: '#fff',
          borderRadius: '8px',
          maxWidth: '800px',
          width: '90%',
          maxHeight: '80vh',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          style={{
            padding: '24px',
            borderBottom: '1px solid #e0e0e0',
          }}
        >
          <h2 style={{ margin: 0, fontSize: '24px', fontWeight: 600 }}>
            Select Notebooks to Sync
          </h2>
          <p style={{ margin: '8px 0 0 0', color: '#666', fontSize: '14px' }}>
            Choose which notebooks you want to include in your RAG system
          </p>
        </div>

        {/* Content */}
        <div
          style={{
            padding: '24px',
            flex: 1,
            overflowY: 'auto',
          }}
        >
          {loading ? (
            <div style={{ textAlign: 'center', padding: '48px', color: '#666' }}>
              <div
                style={{
                  display: 'inline-block',
                  width: '40px',
                  height: '40px',
                  border: '4px solid #f3f3f3',
                  borderTop: '4px solid #1976d2',
                  borderRadius: '50%',
                  animation: 'spin 1s linear infinite',
                }}
              />
              <p style={{ marginTop: '16px' }}>Discovering notebooks...</p>
              <style>
                {`
                  @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                  }
                `}
              </style>
            </div>
          ) : error ? (
            <div
              style={{
                padding: '16px',
                backgroundColor: '#ffebee',
                color: '#c62828',
                borderRadius: '4px',
                marginBottom: '16px',
              }}
            >
              <strong>Error:</strong> {error}
              <button
                onClick={fetchDiscoveredNotebooks}
                style={{
                  marginLeft: '12px',
                  padding: '4px 12px',
                  border: 'none',
                  backgroundColor: '#c62828',
                  color: '#fff',
                  borderRadius: '4px',
                  cursor: 'pointer',
                }}
              >
                Retry
              </button>
            </div>
          ) : (
            <NotebookList
              notebooks={notebooks}
              selectedIds={selectedIds}
              onToggle={toggleNotebook}
            />
          )}
        </div>

        {/* Footer */}
        <div
          style={{
            padding: '16px 24px',
            borderTop: '1px solid #e0e0e0',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <div style={{ color: '#666', fontSize: '14px' }}>
            {selectedIds.size} notebook(s) selected
          </div>

          <div style={{ display: 'flex', gap: '12px' }}>
            <button
              onClick={onClose}
              disabled={saving}
              style={{
                padding: '10px 20px',
                border: '1px solid #ddd',
                backgroundColor: '#fff',
                borderRadius: '4px',
                cursor: saving ? 'not-allowed' : 'pointer',
                fontSize: '14px',
                fontWeight: 500,
              }}
            >
              Cancel
            </button>

            <button
              onClick={handleSyncSelected}
              disabled={saving || selectedIds.size === 0}
              style={{
                padding: '10px 20px',
                border: 'none',
                backgroundColor:
                  saving || selectedIds.size === 0 ? '#ccc' : '#1976d2',
                color: '#fff',
                borderRadius: '4px',
                cursor:
                  saving || selectedIds.size === 0 ? 'not-allowed' : 'pointer',
                fontSize: '14px',
                fontWeight: 500,
              }}
            >
              {saving
                ? 'Saving...'
                : `Sync ${selectedIds.size} Notebook${selectedIds.size !== 1 ? 's' : ''}`}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
