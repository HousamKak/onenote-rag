import { Palette } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';

const ThemeSwitcher = () => {
  const { theme, toggleTheme } = useTheme();

  if (theme === 'brutalist') {
    return (
      <button
        onClick={toggleTheme}
        className="flex items-center gap-2 px-4 py-2.5 bg-neo-purple text-white border-4 border-neo-black shadow-brutal hover:shadow-brutal-hover hover:translate-x-1 hover:translate-y-1 active:shadow-none active:translate-x-2 active:translate-y-2 font-black uppercase text-sm"
        title="Switch to Claude Theme"
      >
        <Palette size={18} strokeWidth={3} />
        <span className="hidden sm:inline">CLAUDE MODE</span>
      </button>
    );
  }

  return (
    <button
      onClick={toggleTheme}
      className="flex items-center gap-2 px-4 py-2.5 bg-claude-primary hover:bg-claude-primary-hover text-white rounded-lg shadow-claude font-medium text-sm"
      title="Switch to Brutalist Theme"
    >
      <Palette size={18} />
      <span className="hidden sm:inline">Brutalist Mode</span>
    </button>
  );
};

export default ThemeSwitcher;
