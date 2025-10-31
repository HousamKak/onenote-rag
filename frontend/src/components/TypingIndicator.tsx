import { useTheme } from '../context/ThemeContext';

const TypingIndicator = () => {
  const { theme } = useTheme();

  if (theme === 'claude') {
    return (
      <div className="flex items-start max-w-3xl animate-fadeInUp">
        <div className="bg-claude-surface rounded-2xl px-4 py-3 shadow-claude">
          <div className="flex gap-1.5 items-center">
            <div className="w-2.5 h-2.5 bg-claude-accent rounded-full animate-bounce" />
            <div className="w-2.5 h-2.5 bg-claude-accent rounded-full animate-bounce [animation-delay:0.15s]" />
            <div className="w-2.5 h-2.5 bg-claude-accent rounded-full animate-bounce [animation-delay:0.3s]" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-start gap-4 max-w-3xl animate-fadeInUp">
      <div className="w-12 h-12 bg-neo-pink border-4 border-neo-black shadow-brutal-sm flex items-center justify-center flex-shrink-0 animate-wiggle">
        <span className="text-neo-black text-lg font-black">AI</span>
      </div>
      <div className="bg-white border-4 border-neo-black shadow-brutal px-5 py-4">
        <div className="flex gap-2">
          <div className="w-3 h-3 bg-neo-pink border-2 border-neo-black animate-bounce" />
          <div className="w-3 h-3 bg-neo-yellow border-2 border-neo-black animate-bounce [animation-delay:0.15s]" />
          <div className="w-3 h-3 bg-neo-cyan border-2 border-neo-black animate-bounce [animation-delay:0.3s]" />
        </div>
      </div>
    </div>
  );
};

export default TypingIndicator;
