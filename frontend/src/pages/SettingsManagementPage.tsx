import { useState, useEffect } from 'react';
import { Save, AlertCircle, CheckCircle2, Eye, EyeOff, ChevronDown, ChevronUp } from 'lucide-react';
import axios from 'axios';
import { useTheme } from '../context/ThemeContext';
 
interface Setting {
  key: string;
  value: string;
  is_sensitive: boolean;
  description: string | null;
  has_value: boolean;
}
 
const API_BASE_URL = 'http://localhost:8000/api';
 
export default function SettingsManagementPage() {
  const { theme } = useTheme();
  const [settings, setSettings] = useState<Setting[]>([]);
  const [editedValues, setEditedValues] = useState<Record<string, string>>({});
  const [showSensitive, setShowSensitive] = useState<Record<string, boolean>>({});
  const [showOptionalSettings, setShowOptionalSettings] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testingConnection, setTestingConnection] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<{ status: string; message: string } | null>(null);
 
  useEffect(() => {
    fetchSettings();
  }, []);
 
  const fetchSettings = async () => {
    try {
      setLoading(true);
 
      const response = await axios.get<Setting[]>(`${API_BASE_URL}/settings`);
      setSettings(response.data);
 
      // Initialize edited values with current values
      const initialValues: Record<string, string> = {};
      response.data.forEach((setting) => {
        initialValues[setting.key] = setting.value;
      });
      setEditedValues(initialValues);
    } catch (error) {
      console.error('Failed to fetch settings:', error);
      setMessage({ type: 'error', text: 'Failed to load settings' });
    } finally {
      setLoading(false);
    }
  };
 
  const handleValueChange = (key: string, value: string) => {
    setEditedValues((prev) => ({ ...prev, [key]: value }));
  };
 
  const toggleShowSensitive = (key: string) => {
    setShowSensitive((prev) => ({ ...prev, [key]: !prev[key] }));
  };
 
  const saveSetting = async (key: string, valueOverride?: string) => {
    try {
      setSaving(true);
     
      // Get current setting
      const currentSetting = settings.find(s => s.key === key);
     
     
      // Determine value to save
      const newValue = valueOverride !== undefined
        ? valueOverride
        : (editedValues[key] !== undefined ? editedValues[key] : currentSetting?.value || '');
 
      // Send update to backend
      await axios.put(`${API_BASE_URL}/settings/${key}`, {
        value: newValue
      });
     
      // Update local state
      setSettings(prevSettings => {
        const updated = prevSettings.map(s =>
          s.key === key ? { ...s, value: newValue, has_value: newValue !== '' } : s
        );
        return updated;
      });
     
      // Sync editedValues
      setEditedValues(prev => ({
        ...prev,
        [key]: newValue
      }));
     
      setMessage({ type: 'success', text: `${key} saved successfully` });
      setTimeout(() => setMessage(null), 3000);
    } catch (error: any) {
      console.error(`Failed to save setting '${key}':`, error);
      setMessage({ type: 'error', text: `Failed to save ${key}` });
    } finally {
      setSaving(false);
    }
  };
 
  const saveAllSettings = async () => {
    try {
      setSaving(true);
     
      // Save all modified settings
      const promises = Object.entries(editedValues).map(([key, value]) => {
        const original = settings.find((s) => s.key === key);
        if (original && original.value !== value) {
          return axios.put(`${API_BASE_URL}/settings/${key}`, { value });
        }
        return Promise.resolve();
      });
     
      await Promise.all(promises);
     
      setMessage({ type: 'success', text: 'All settings saved successfully' });
      setTimeout(() => setMessage(null), 3000);
     
      // Refresh settings
      await fetchSettings();
    } catch (error) {
      console.error('Failed to save settings:', error);
      setMessage({ type: 'error', text: 'Failed to save some settings' });
    } finally {
      setSaving(false);
    }
  };
 
  const clearSetting = async (key: string) => {
    try {
      setSaving(true);
      await axios.put(`${API_BASE_URL}/settings/${key}`, {
        value: '',
      });
     
      setMessage({ type: 'success', text: `${key} cleared successfully` });
      setTimeout(() => setMessage(null), 3000);
     
      // Refresh settings to get updated values
      await fetchSettings();
    } catch (error) {
      console.error('Failed to clear setting:', error);
      setMessage({ type: 'error', text: `Failed to clear ${key}` });
    } finally {
      setSaving(false);
    }
  };
 
  const testOpenAIConnection = async () => {
    try {
      setTestingConnection(true);
      setConnectionStatus(null);
     
      const response = await axios.post(`${API_BASE_URL}/settings/test-connection`);
      setConnectionStatus(response.data);
    } catch (error) {
      console.error('Connection test failed:', error);
      setConnectionStatus({
        status: 'error',
        message: 'Failed to test connection',
      });
    } finally {
      setTestingConnection(false);
    }
  };
 
  const testOneNoteConnection = async () => {
    try {
      setTestingConnection(true);
      setConnectionStatus(null);
     
      const authMethod = editedValues['use_azure_ad_auth'] === 'true' ? 'Azure AD' : 'Manual Token';
      const response = await axios.get(`${API_BASE_URL}/onenote/notebooks`);
     
      setConnectionStatus({
        status: 'success',
        message: `Connected successfully using ${authMethod}! Found ${response.data.notebooks.length} notebook(s).`,
      });
    } catch (error: any) {
      const authMethod = editedValues['use_azure_ad_auth'] === 'true' ? 'Azure AD' : 'Manual Token';
      console.error(`OneNote connection test failed using ${authMethod}:`, error);
     
      setConnectionStatus({
        status: 'error',
        message: `Failed to connect using ${authMethod}: ${error.response?.data?.detail || error.message}`,
      });
    } finally {
      setTestingConnection(false);
    }
  };
 
  const getSensitiveInputType = (key: string) => {
    return showSensitive[key] ? 'text' : 'password';
  };
 
  const renderInput = (setting: Setting) => {
    // Use editedValues if present, otherwise fall back to the setting's actual value
    const value = editedValues[setting.key] !== undefined ? editedValues[setting.key] : setting.value;
    const hasChanged = value !== setting.value;
 
    // Special handling for boolean toggle settings (auto-save on toggle)
    const isBooleanSetting = setting.key === 'use_azure_ad_auth' || setting.key === 'enable_startup_sync';
   
    if (isBooleanSetting && theme === 'claude') {
      const isEnabled = value === 'true';
     
      const handleToggle = async () => {
        const newValue = isEnabled ? 'false' : 'true';
        handleValueChange(setting.key, newValue);
        await saveSetting(setting.key, newValue);
      };
     
      return (
        <div key={setting.key} className="border border-claude-border rounded-lg p-4 bg-white hover:border-claude-primary transition-colors h-full flex flex-col">
          <div className="flex items-start justify-between mb-2">
            <div className="flex-1 min-w-0">
              <label className="block text-sm font-semibold text-claude-text mb-1 truncate" title={setting.key}>
                {setting.key}
              </label>
              {setting.description && (
                <p className="text-xs text-claude-text-secondary line-clamp-2">{setting.description}</p>
              )}
            </div>
          </div>
 
          <div className="flex items-center gap-3 mt-auto">
            <div className="flex items-center gap-2 flex-1">
              <span className="text-sm font-medium text-claude-text">
                {isEnabled ? (setting.key === 'use_azure_ad_auth' ? 'Azure AD' : 'Enabled') : (setting.key === 'use_azure_ad_auth' ? 'Manual Token' : 'Disabled')}
              </span>
              <button
                onClick={handleToggle}
                disabled={saving}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  isEnabled ? 'bg-claude-primary' : 'bg-gray-300'
                } ${saving ? 'opacity-50 cursor-not-allowed' : ''}`}
                role="switch"
                aria-checked={isEnabled}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    isEnabled ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>
          </div>
        </div>
      );
    }
 
    if (theme === 'claude') {
      return (
        <div key={setting.key} className="border border-claude-border rounded-lg p-4 bg-white hover:border-claude-primary transition-colors h-full flex flex-col">
          <div className="flex items-start justify-between mb-2">
            <div className="flex-1 min-w-0">
              <label className="block text-sm font-semibold text-claude-text mb-1 truncate" title={setting.key}>
                {setting.key}
              </label>
              {setting.description && (
                <p className="text-xs text-claude-text-secondary line-clamp-2">{setting.description}</p>
              )}
            </div>
            {setting.is_sensitive && (
              <span className="ml-2 px-2 py-0.5 bg-red-100 text-red-700 text-xs font-medium rounded flex-shrink-0">
                Sensitive
              </span>
            )}
          </div>
 
          <div className="flex gap-2 mt-auto">
            <div className="flex-1 relative">
              <input
                type={setting.is_sensitive ? getSensitiveInputType(setting.key) : 'text'}
                value={value}
                onChange={(e) => handleValueChange(setting.key, e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-claude-primary focus:border-transparent focus:outline-none font-mono text-xs"
                placeholder={setting.is_sensitive && setting.has_value ? '••••••••' : `Enter ${setting.key}`}
              />
              {setting.is_sensitive && (
                <button
                  onClick={() => toggleShowSensitive(setting.key)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 p-1 hover:bg-gray-100 rounded"
                  aria-label="Toggle visibility"
                >
                  {showSensitive[setting.key] ? (
                    <EyeOff className="w-4 h-4 text-gray-500" />
                  ) : (
                    <Eye className="w-4 h-4 text-gray-500" />
                  )}
                </button>
              )}
            </div>
           
            <button
              onClick={() => saveSetting(setting.key)}
              disabled={!hasChanged || saving}
              aria-label={`Save ${setting.key}`}
              className={`px-3 py-2 rounded-lg font-medium shadow-claude transition-all flex items-center gap-1 flex-shrink-0 ${
                hasChanged && !saving
                  ? 'bg-claude-primary hover:bg-claude-primary-hover text-white'
                  : 'bg-gray-200 text-gray-400 cursor-not-allowed'
              }`}
            >
              <Save className="w-4 h-4" />
            </button>
           
            {setting.has_value && (
              <button
                onClick={() => clearSetting(setting.key)}
                disabled={saving}
                aria-label={`Clear ${setting.key}`}
                className="px-3 py-2 rounded-lg font-medium shadow-claude transition-all flex items-center gap-1 flex-shrink-0 bg-red-500 hover:bg-red-600 text-white disabled:bg-gray-200 disabled:text-gray-400 disabled:cursor-not-allowed"
              >
                <AlertCircle className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
      );
    }
 
    // Special handling for boolean toggle settings in neo-brutalism theme (auto-save on toggle)
    if (isBooleanSetting) {
      const isEnabled = value === 'true';
     
      const handleToggle = async () => {
        const newValue = isEnabled ? 'false' : 'true';
        handleValueChange(setting.key, newValue);
        await saveSetting(setting.key, newValue);
      };
     
      return (
        <div key={setting.key} className="border-2 border-black p-4 bg-white shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] h-full flex flex-col">
          <div className="flex items-start justify-between mb-2">
            <div className="flex-1 min-w-0">
              <label className="block text-base font-bold mb-1 truncate" title={setting.key}>{setting.key}</label>
              {setting.description && (
                <p className="text-xs text-gray-600 mb-2 line-clamp-2">{setting.description}</p>
              )}
            </div>
          </div>
 
          <div className="flex items-center gap-3 mt-auto">
            <div className="flex items-center gap-2 flex-1">
              <span className="text-sm font-bold">
                {isEnabled ? (setting.key === 'use_azure_ad_auth' ? 'AZURE AD' : 'ENABLED') : (setting.key === 'use_azure_ad_auth' ? 'MANUAL TOKEN' : 'DISABLED')}
              </span>
              <button
                onClick={handleToggle}
                disabled={saving}
                className={`relative inline-flex h-7 w-14 items-center rounded-full border-2 border-black transition-colors ${
                  isEnabled ? 'bg-blue-400' : 'bg-gray-300'
                } ${saving ? 'opacity-50 cursor-not-allowed' : ''}`}
                role="switch"
                aria-checked={isEnabled}
              >
                <span
                  className={`inline-block h-5 w-5 transform rounded-full bg-white border-2 border-black transition-transform ${
                    isEnabled ? 'translate-x-7' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>
          </div>
        </div>
      );
    }
 
    // Neo-brutalism theme (regular inputs)
    return (
      <div key={setting.key} className="border-2 border-black p-4 bg-white shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] h-full flex flex-col">
        <div className="flex items-start justify-between mb-2">
          <div className="flex-1 min-w-0">
            <label className="block text-base font-bold mb-1 truncate" title={setting.key}>{setting.key}</label>
            {setting.description && (
              <p className="text-xs text-gray-600 mb-2 line-clamp-2">{setting.description}</p>
            )}
          </div>
          {setting.is_sensitive && (
            <span className="ml-2 px-2 py-0.5 bg-red-200 border-2 border-black text-xs font-bold flex-shrink-0">
              SENSITIVE
            </span>
          )}
        </div>
 
        <div className="flex gap-2 mt-auto">
          <div className="flex-1 relative">
            <input
              type={setting.is_sensitive ? getSensitiveInputType(setting.key) : 'text'}
              value={value}
              onChange={(e) => handleValueChange(setting.key, e.target.value)}
              className="w-full px-3 py-2 border-2 border-black focus:ring-2 focus:ring-blue-500 focus:outline-none font-mono text-xs"
              placeholder={setting.is_sensitive && setting.has_value ? '••••••••' : `Enter ${setting.key}`}
            />
            {setting.is_sensitive && (
              <button
                onClick={() => toggleShowSensitive(setting.key)}
                className="absolute right-2 top-1/2 -translate-y-1/2 p-2 hover:bg-gray-100"
                aria-label="Toggle visibility"
              >
                {showSensitive[setting.key] ? (
                  <EyeOff className="w-4 h-4" />
                ) : (
                  <Eye className="w-4 h-4" />
                )}
              </button>
            )}
          </div>
         
          <button
            onClick={() => saveSetting(setting.key)}
            disabled={!hasChanged || saving}
            aria-label={`Save ${setting.key}`}
            className={`px-3 py-2 border-2 border-black font-bold shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] active:shadow-none active:translate-x-1 active:translate-y-1 transition-all flex-shrink-0 ${
              hasChanged && !saving
                ? 'bg-blue-400 hover:bg-blue-500'
                : 'bg-gray-200 cursor-not-allowed'
            }`}
          >
            <Save className="w-5 h-5" />
          </button>
         
          {setting.has_value && (
            <button
              onClick={() => clearSetting(setting.key)}
              disabled={saving}
              aria-label={`Clear ${setting.key}`}
              className="px-3 py-2 border-2 border-black font-bold shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] active:shadow-none active:translate-x-1 active:translate-y-1 transition-all flex-shrink-0 bg-red-400 hover:bg-red-500 disabled:bg-gray-200 disabled:cursor-not-allowed"
            >
              <AlertCircle className="w-5 h-5" />
            </button>
          )}
        </div>
      </div>
    );
  };
 
  if (loading) {
    return (
      <div className={`min-h-screen p-8 ${theme === 'claude' ? 'bg-white' : 'bg-yellow-50'}`}>
        <div className="max-w-4xl mx-auto">
          <div className={`text-center text-xl ${theme === 'claude' ? 'font-medium text-claude-text' : 'font-bold'}`}>
            Loading settings...
          </div>
        </div>
      </div>
    );
  }
 
  return (
    <div className={`h-full overflow-y-auto p-6 ${theme === 'claude' ? 'bg-white' : 'bg-yellow-50'}`}>
      <div className="max-w-6xl mx-auto pb-20">
        {/* Header */}
        <div className="mb-6">
          {theme === 'claude' ? (
            <>
              <h1 className="text-3xl font-semibold text-claude-text mb-3">
                API Keys & Settings
              </h1>
              <p className="text-base text-claude-text-secondary">
                Configure your API keys and application settings. All sensitive data is encrypted and stored securely.
              </p>
            </>
          ) : (
            <>
              <h1 className="text-4xl font-black mb-4 transform -rotate-1">
                ⚙️ Settings Management
              </h1>
              <p className="text-lg">
                Configure your API keys and application settings. Changes are encrypted and stored securely.
              </p>
            </>
          )}
        </div>
 
        {/* Message Banner */}
        {message && (
          <div
            className={theme === 'claude'
              ? `mb-6 p-4 rounded-lg border ${
                  message.type === 'success'
                    ? 'bg-green-50 border-green-200 text-green-800'
                    : 'bg-red-50 border-red-200 text-red-800'
                }`
              : `mb-6 p-4 border-2 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] ${
                  message.type === 'success' ? 'bg-green-300' : 'bg-red-300'
                }`
            }
          >
            <div className="flex items-center gap-2">
              {message.type === 'success' ? (
                <CheckCircle2 className="w-5 h-5" />
              ) : (
                <AlertCircle className="w-5 h-5" />
              )}
              <span className={theme === 'claude' ? 'font-medium' : 'font-bold'}>{message.text}</span>
            </div>
          </div>
        )}
 
        {/* Connection Tests */}
        <div className={theme === 'claude'
          ? 'mb-6 p-4 border border-claude-border rounded-lg bg-gray-50'
          : 'mb-6 p-4 border-2 border-black bg-white shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]'
        }>
          <h3 className={theme === 'claude' ? 'font-semibold text-base mb-3 text-claude-text' : 'font-bold text-base mb-3'}>
            Test Connections
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {/* OpenAI Test */}
            <div className={theme === 'claude' ? 'p-3 bg-white rounded border border-gray-200' : 'p-3 bg-yellow-50 border-2 border-black'}>
              <div className="flex items-center justify-between mb-2">
                <span className={theme === 'claude' ? 'text-sm font-medium' : 'text-sm font-bold'}>OpenAI API</span>
                <button
                  onClick={testOpenAIConnection}
                  disabled={testingConnection}
                  className={theme === 'claude'
                    ? 'px-3 py-1 bg-claude-primary text-white text-xs rounded font-medium hover:bg-claude-primary-hover disabled:bg-gray-300'
                    : 'px-3 py-1 bg-purple-400 border border-black text-xs font-bold hover:bg-purple-500 disabled:bg-gray-200'
                  }
                >
                  {testingConnection ? 'Testing...' : 'Test'}
                </button>
              </div>
            </div>
           
            {/* OneNote Test */}
            <div className={theme === 'claude' ? 'p-3 bg-white rounded border border-gray-200' : 'p-3 bg-blue-50 border-2 border-black'}>
              <div className="flex items-center justify-between mb-2">
                <div>
                  <span className={theme === 'claude' ? 'text-sm font-medium' : 'text-sm font-bold'}>OneNote</span>
                  <p className={theme === 'claude' ? 'text-xs text-claude-text-secondary' : 'text-xs text-gray-600'}>
                    {editedValues['use_azure_ad_auth'] === 'true' ? 'via Azure AD' : 'via Manual Token'}
                  </p>
                </div>
                <button
                  onClick={testOneNoteConnection}
                  disabled={testingConnection}
                  className={theme === 'claude'
                    ? 'px-3 py-1 bg-claude-primary text-white text-xs rounded font-medium hover:bg-claude-primary-hover disabled:bg-gray-300'
                    : 'px-3 py-1 bg-blue-400 border border-black text-xs font-bold hover:bg-blue-500 disabled:bg-gray-200'
                  }
                >
                  {testingConnection ? 'Testing...' : 'Test'}
                </button>
              </div>
            </div>
          </div>
         
          {connectionStatus && (
            <div
              className={theme === 'claude'
                ? `mt-3 p-3 rounded-lg text-sm ${
                    connectionStatus.status === 'success' ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'
                  }`
                : `mt-3 p-3 border-2 border-black text-sm ${
                    connectionStatus.status === 'success' ? 'bg-green-200' : 'bg-red-200'
                  }`
              }
            >
              <p className={theme === 'claude' ? 'font-medium' : 'font-bold'}>{connectionStatus.message}</p>
            </div>
          )}
        </div>
 
        {/* Settings List - Separated by Sensitive and Optional */}
        <div className="mb-6 space-y-6">
          {/* Sensitive Settings Section */}
          <div>
            <h2 className={theme === 'claude'
              ? 'text-xl font-semibold text-claude-text mb-4'
              : 'text-2xl font-black mb-4'
            }>
              🔐 API Keys & Credentials
            </h2>
           
            {/* Microsoft Authentication Toggle */}
            <div className={theme === 'claude'
              ? 'mb-3 p-3 bg-blue-50 border border-blue-200 rounded'
              : 'mb-3 p-3 bg-blue-100 border-2 border-black'
            }>
              <div className="flex items-center justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className={theme === 'claude' ? 'font-medium text-xs text-claude-text' : 'font-bold text-xs'}>
                      Microsoft Auth:
                    </span>
                    <span className={theme === 'claude' ? 'text-xs text-claude-text-secondary' : 'text-xs text-gray-600'}>
                      {editedValues['use_azure_ad_auth'] === 'true' ? 'Azure AD' : 'Manual Token'}
                    </span>
                  </div>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={editedValues['use_azure_ad_auth'] === 'true'}
                    onChange={async (e) => {
                      const newValue = e.target.checked ? 'true' : 'false';
                      handleValueChange('use_azure_ad_auth', newValue);
                      await saveSetting('use_azure_ad_auth', newValue);
                    }}
                    className="sr-only peer"
                  />
                  <div className="w-9 h-5 bg-gray-300 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-blue-600"></div>
                  <span className={`ml-2 text-xs font-medium ${theme === 'claude' ? 'text-claude-text' : 'text-gray-900'}`}>
                    Azure AD
                  </span>
                </label>
              </div>
            </div>
 
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {settings.filter(s => s.is_sensitive).map((setting) => renderInput(setting))}
            </div>
          </div>
 
          {/* Optional Settings Section - Collapsible */}
          <div>
            <button
              onClick={() => setShowOptionalSettings(!showOptionalSettings)}
              className={theme === 'claude'
                ? 'flex items-center gap-2 text-lg font-semibold text-claude-text hover:text-claude-primary transition-colors mb-4 w-full'
                : 'flex items-center gap-2 text-xl font-black hover:translate-x-1 transition-transform mb-4 w-full'
              }
            >
              {showOptionalSettings ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
              <span>⚙️ Application Settings ({settings.filter(s => !s.is_sensitive).length})</span>
            </button>
           
            {showOptionalSettings && (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {settings.filter(s => !s.is_sensitive).map((setting) => renderInput(setting))}
              </div>
            )}
          </div>
        </div>
 
        {/* Save All Button */}
        <div className="flex justify-end mb-6">
          <button
            onClick={saveAllSettings}
            disabled={saving}
            className={theme === 'claude'
              ? `px-6 py-3 bg-claude-primary text-white rounded-lg font-medium text-base shadow-claude hover:bg-claude-primary-hover transition-all disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center gap-2`
              : `px-8 py-4 bg-green-400 border-2 border-black font-bold text-lg shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:bg-green-500 active:shadow-none active:translate-x-1 active:translate-y-1 transition-all disabled:bg-gray-200 disabled:cursor-not-allowed flex items-center gap-2`
            }
          >
            <Save className="w-6 h-6" />
            {saving ? 'Saving...' : 'Save All Settings'}
          </button>
        </div>
 
        {/* Help Text */}
        <div className={theme === 'claude'
          ? 'mt-8 p-5 border border-blue-200 bg-blue-50 rounded-lg'
          : 'mt-8 p-6 border-2 border-black bg-blue-100 shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]'
        }>
          <h3 className={theme === 'claude' ? 'font-semibold text-lg mb-3 text-claude-text' : 'font-bold text-lg mb-2'}>
            {theme === 'claude' ? 'Important Information' : '💡 Important Notes'}
          </h3>
          <ul className={`space-y-2 ${theme === 'claude' ? 'text-sm text-claude-text-secondary' : 'text-sm'}`}>
            <li>• API keys are encrypted before storage</li>
            <li>• Settings are stored in a local SQLite database</li>
            <li>• Changes take effect immediately after saving</li>
            <li>• Sensitive values are masked by default (click the eye icon to reveal)</li>
            <li>• The .env file is used as a fallback if database values are not set</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
 