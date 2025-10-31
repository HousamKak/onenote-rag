import { AlertTriangle, X } from 'lucide-react';
import { createPortal } from 'react-dom';
import { useTheme } from '../context/ThemeContext';

interface ConfirmModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  variant?: 'danger' | 'warning';
}

const ConfirmModal = ({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  variant = 'danger',
}: ConfirmModalProps) => {
  const { theme } = useTheme();

  if (!isOpen) return null;

  const handleConfirm = () => {
    onConfirm();
    onClose();
  };

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  const modalContent = theme === 'claude' ? (
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center p-4"
      style={{ zIndex: 9999 }}
      onClick={handleBackdropClick}
    >
      <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full animate-in">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div className="flex items-center gap-3">
            <div
              className={`w-10 h-10 rounded-full flex items-center justify-center ${
                variant === 'danger' ? 'bg-red-100' : 'bg-yellow-100'
              }`}
            >
              <AlertTriangle
                size={20}
                className={variant === 'danger' ? 'text-red-600' : 'text-yellow-600'}
              />
            </div>
            <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        {/* Body */}
        <div className="p-6">
          <p className="text-sm text-gray-600 leading-relaxed">{message}</p>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-3 p-6 bg-gray-50 rounded-b-2xl">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2.5 border border-gray-300 rounded-lg hover:bg-white transition-colors text-sm font-medium text-gray-700"
          >
            {cancelText}
          </button>
          <button
            onClick={handleConfirm}
            className={`flex-1 px-4 py-2.5 rounded-lg transition-colors text-sm font-medium text-white ${
              variant === 'danger'
                ? 'bg-red-600 hover:bg-red-700'
                : 'bg-yellow-600 hover:bg-yellow-700'
            }`}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  ) : (
    <div
      className="fixed inset-0 bg-neo-black/70 flex items-center justify-center p-4"
      style={{ zIndex: 9999 }}
      onClick={handleBackdropClick}
    >
      <div className="bg-white border-8 border-neo-black shadow-brutal-xl max-w-md w-full">
        {/* Header */}
        <div className="bg-neo-yellow border-b-8 border-neo-black p-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div
              className={`w-12 h-12 border-4 border-neo-black flex items-center justify-center shadow-brutal-sm ${
                variant === 'danger' ? 'bg-neo-pink' : 'bg-neo-orange'
              }`}
            >
              <AlertTriangle size={24} className="text-neo-black" strokeWidth={3} />
            </div>
            <h3 className="text-xl font-black text-neo-black uppercase tracking-tight">
              {title}
            </h3>
          </div>
          <button
            onClick={onClose}
            className="w-10 h-10 bg-white border-4 border-neo-black hover:bg-neo-lime shadow-brutal-sm hover:shadow-brutal hover:translate-x-1 hover:translate-y-1 active:shadow-none active:translate-x-2 active:translate-y-2 flex items-center justify-center"
          >
            <X size={20} className="text-neo-black" strokeWidth={3} />
          </button>
        </div>

        {/* Body */}
        <div className="p-6">
          <p className="text-base font-bold text-neo-black leading-relaxed">{message}</p>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-3 p-4 bg-neo-yellow border-t-8 border-neo-black">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-3 bg-white border-4 border-neo-black shadow-brutal hover:shadow-brutal-hover hover:translate-x-1 hover:translate-y-1 active:shadow-none active:translate-x-2 active:translate-y-2 font-black text-sm uppercase text-neo-black"
          >
            {cancelText}
          </button>
          <button
            onClick={handleConfirm}
            className={`flex-1 px-4 py-3 border-4 border-neo-black shadow-brutal hover:shadow-brutal-hover hover:translate-x-1 hover:translate-y-1 active:shadow-none active:translate-x-2 active:translate-y-2 font-black text-sm uppercase text-neo-black ${
              variant === 'danger' ? 'bg-neo-pink' : 'bg-neo-orange'
            }`}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  );

  return createPortal(modalContent, document.body);
};

export default ConfirmModal;
