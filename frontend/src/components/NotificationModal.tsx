import { CheckCircle, XCircle, X } from 'lucide-react';
import { useEffect } from 'react';

interface NotificationModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  message: string;
  variant?: 'success' | 'error';
  autoClose?: boolean;
  autoCloseDelay?: number;
}

const NotificationModal = ({
  isOpen,
  onClose,
  title,
  message,
  variant = 'success',
  autoClose = true,
  autoCloseDelay = 3000,
}: NotificationModalProps) => {
  useEffect(() => {
    if (isOpen && autoClose) {
      const timer = setTimeout(() => {
        onClose();
      }, autoCloseDelay);
      return () => clearTimeout(timer);
    }
  }, [isOpen, autoClose, autoCloseDelay, onClose]);

  if (!isOpen) return null;

  const variantStyles = {
    success: {
      bgColor: 'bg-green-50',
      borderColor: 'border-green-200',
      iconColor: 'text-green-600',
      titleColor: 'text-green-900',
      messageColor: 'text-green-700',
      Icon: CheckCircle,
    },
    error: {
      bgColor: 'bg-red-50',
      borderColor: 'border-red-200',
      iconColor: 'text-red-600',
      titleColor: 'text-red-900',
      messageColor: 'text-red-700',
      Icon: XCircle,
    },
  };

  const styles = variantStyles[variant];
  const { Icon } = styles;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 px-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/20 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Notification */}
      <div
        className={`relative ${styles.bgColor} ${styles.borderColor} border-2 rounded-lg shadow-lg max-w-md w-full p-4 animate-slideDown`}
      >
        <div className="flex items-start gap-3">
          <Icon className={`${styles.iconColor} flex-shrink-0 mt-0.5`} size={24} />

          <div className="flex-1 min-w-0">
            <h3 className={`text-sm font-semibold ${styles.titleColor} mb-1`}>
              {title}
            </h3>
            <p className={`text-sm ${styles.messageColor}`}>
              {message}
            </p>
          </div>

          <button
            onClick={onClose}
            className="flex-shrink-0 text-gray-400 hover:text-gray-600 transition-colors"
            aria-label="Close notification"
          >
            <X size={18} />
          </button>
        </div>
      </div>
    </div>
  );
};

export default NotificationModal;
