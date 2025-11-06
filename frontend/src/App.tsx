import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider } from './context/ThemeContext';
import Layout from './components/Layout';
import ChatPage from './pages/ChatPage';
import ConfigPage from './pages/ConfigPage';
import IndexPage from './pages/IndexPage';
import ComparePage from './pages/ComparePage';
import SettingsManagementPage from './pages/SettingsManagementPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

function App() {
  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Layout />}>
              <Route index element={<Navigate to="/query" replace />} />
              <Route path="query" element={<ChatPage />} />
              <Route path="config" element={<ConfigPage />} />
              <Route path="index" element={<IndexPage />} />
              <Route path="compare" element={<ComparePage />} />
              <Route path="settings" element={<SettingsManagementPage />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </QueryClientProvider>
    </ThemeProvider>
  );
}

export default App;
