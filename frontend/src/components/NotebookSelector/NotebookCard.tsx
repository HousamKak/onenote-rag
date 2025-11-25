import React from 'react';
import type { Notebook } from '../../types';

interface NotebookCardProps {
  notebook: Notebook;
  isSelected: boolean;
  onToggle: () => void;
}

export const NotebookCard: React.FC<NotebookCardProps> = ({
  notebook,
  isSelected,
  onToggle,
}) => {
  return (
    <div
      className={`notebook-card ${isSelected ? 'selected' : ''}`}
      style={{
        border: '1px solid #ddd',
        borderRadius: '8px',
        padding: '16px',
        marginBottom: '12px',
        cursor: 'pointer',
        backgroundColor: isSelected ? '#e3f2fd' : '#fff',
        transition: 'all 0.2s',
      }}
      onClick={onToggle}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        {/* Checkbox */}
        <input
          type="checkbox"
          checked={isSelected}
          onChange={onToggle}
          onClick={(e) => e.stopPropagation()}
          style={{ width: '20px', height: '20px', cursor: 'pointer' }}
        />

        {/* Notebook Info */}
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <h4 style={{ margin: 0, fontSize: '16px', fontWeight: 600 }}>
              {notebook.displayName}
            </h4>

            {/* Badges */}
            {notebook.isShared && (
              <span
                style={{
                  padding: '2px 8px',
                  fontSize: '12px',
                  borderRadius: '12px',
                  backgroundColor: '#fff3e0',
                  color: '#e65100',
                  fontWeight: 500,
                }}
              >
                Shared by {notebook.sharedBy || 'Unknown'}
              </span>
            )}

            <span
              style={{
                padding: '2px 8px',
                fontSize: '12px',
                borderRadius: '12px',
                backgroundColor: '#f5f5f5',
                color: '#666',
              }}
            >
              {notebook.userRole || 'Unknown role'}
            </span>
          </div>

          {/* Last Modified */}
          {notebook.lastModifiedDateTime && (
            <p style={{ margin: '4px 0 0 0', fontSize: '13px', color: '#666' }}>
              Last modified:{' '}
              {new Date(notebook.lastModifiedDateTime).toLocaleDateString()}
            </p>
          )}
        </div>

        {/* External Link */}
        {notebook.webUrl && (
          <a
            href={notebook.webUrl}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            style={{
              padding: '8px',
              borderRadius: '4px',
              color: '#1976d2',
              textDecoration: 'none',
              display: 'flex',
              alignItems: 'center',
            }}
            title="Open in OneNote"
          >
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
              <polyline points="15 3 21 3 21 9" />
              <line x1="10" y1="14" x2="21" y2="3" />
            </svg>
          </a>
        )}
      </div>
    </div>
  );
};
