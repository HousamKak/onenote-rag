import React, { useState } from 'react';
import type { Notebook } from '../../types';
import { NotebookCard } from './NotebookCard';
 
interface NotebookListProps {
  notebooks: Notebook[];
  selectedIds: Set<string>;
  onToggle: (id: string) => void;
}
 
export const NotebookList: React.FC<NotebookListProps> = ({
  notebooks,
  selectedIds,
  onToggle,
}) => {
  const [activeTab, setActiveTab] = useState<'owned' | 'shared' | 'recent'>('owned');
 
  // Separate notebooks by source
  const ownedNotebooks = notebooks.filter((nb) => nb.source === 'owned' || (!nb.source && !nb.isShared));
  const sharedNotebooks = notebooks.filter((nb) => nb.source === 'shared' || (!nb.source && nb.isShared));
  const recentNotebooks = notebooks.filter((nb) => nb.source === 'recent');
 
  const currentNotebooks =
    activeTab === 'owned' ? ownedNotebooks :
    activeTab === 'shared' ? sharedNotebooks :
    recentNotebooks;
 
  return (
    <div>
      {/* Tabs */}
      <div
        style={{
          display: 'flex',
          borderBottom: '2px solid #e0e0e0',
          marginBottom: '16px',
        }}
      >
        <button
          onClick={() => setActiveTab('owned')}
          style={{
            padding: '12px 24px',
            border: 'none',
            background: 'none',
            fontSize: '14px',
            fontWeight: 600,
            cursor: 'pointer',
            borderBottom: activeTab === 'owned' ? '3px solid #1976d2' : 'none',
            color: activeTab === 'owned' ? '#1976d2' : '#666',
            marginBottom: '-2px',
          }}
        >
          My Notebooks ({ownedNotebooks.length})
        </button>
 
        <button
          onClick={() => setActiveTab('shared')}
          style={{
            padding: '12px 24px',
            border: 'none',
            background: 'none',
            fontSize: '14px',
            fontWeight: 600,
            cursor: 'pointer',
            borderBottom: activeTab === 'shared' ? '3px solid #1976d2' : 'none',
            color: activeTab === 'shared' ? '#1976d2' : '#666',
            marginBottom: '-2px',
          }}
        >
          Shared with Me ({sharedNotebooks.length})
        </button>
 
        <button
          onClick={() => setActiveTab('recent')}
          style={{
            padding: '12px 24px',
            border: 'none',
            background: 'none',
            fontSize: '14px',
            fontWeight: 600,
            cursor: 'pointer',
            borderBottom: activeTab === 'recent' ? '3px solid #1976d2' : 'none',
            color: activeTab === 'recent' ? '#1976d2' : '#666',
            marginBottom: '-2px',
          }}
        >
          Recently Accessed ({recentNotebooks.length})
        </button>
      </div>
 
      {/* Notebook List */}
      <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
        {currentNotebooks.length === 0 ? (
          <div
            style={{
              padding: '32px',
              textAlign: 'center',
              color: '#999',
            }}
          >
            {activeTab === 'owned'
              ? 'No owned notebooks found'
              : activeTab === 'shared'
              ? 'No shared notebooks found'
              : 'No recently accessed notebooks found'}
          </div>
        ) : (
          currentNotebooks.map((notebook) => (
            <NotebookCard
              key={notebook.id}
              notebook={notebook}
              isSelected={selectedIds.has(notebook.id)}
              onToggle={() => onToggle(notebook.id)}
            />
          ))
        )}
      </div>
    </div>
  );
};
 