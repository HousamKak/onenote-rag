import type { Message } from '../types/index';
import { useTheme } from '../context/ThemeContext';

interface UserMessageProps {
  message: Message;
}

const UserMessage = ({ message }: UserMessageProps) => {
  const { theme } = useTheme();

  if (theme === 'claude') {
    return (
      <div className="flex items-start gap-3 max-w-3xl ml-auto justify-end">
        <div className="bg-claude-user-msg text-claude-text rounded-2xl px-4 py-3 shadow-claude max-w-[80%]">
          <p className="whitespace-pre-wrap break-words">{message.content}</p>
        </div>
        <div className="w-8 h-8 rounded-full bg-claude-primary flex items-center justify-center flex-shrink-0">
          <span className="text-white text-sm font-semibold">U</span>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-start gap-4 max-w-3xl ml-auto justify-end">
      <div className="bg-neo-blue text-neo-black border-4 border-neo-black shadow-brutal px-5 py-4 max-w-[80%] font-bold">
        <p className="whitespace-pre-wrap break-words leading-snug">{message.content}</p>
      </div>
      <div className="w-12 h-12 bg-neo-yellow border-4 border-neo-black shadow-brutal-sm flex items-center justify-center flex-shrink-0">
        <span className="text-neo-black text-lg font-black">U</span>
      </div>
    </div>
  );
};

export default UserMessage;
