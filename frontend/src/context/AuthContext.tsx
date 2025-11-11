/**
 * Authentication Context for managing user authentication state.
 * Handles login, logout, token management, and user session.
 */
import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

interface User {
  id: string;
  email?: string;
  name?: string;
}

interface AuthContextType {
  user: User | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: () => Promise<void>;
  logout: () => void;
  handleCallback: (code: string, state: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(
    localStorage.getItem('access_token')
  );
  const [isLoading, setIsLoading] = useState(true);

  // Validate token on mount
  useEffect(() => {
    const validateToken = async () => {
      const token = localStorage.getItem('access_token');

      if (token) {
        try {
          // Try to get user info to validate token
          const response = await axios.get(`${API_URL}/auth/user`, {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          });

          setUser(response.data);
          setAccessToken(token);
        } catch (error) {
          console.error('Token validation failed:', error);
          // Token is invalid, clear it
          localStorage.removeItem('access_token');
          setAccessToken(null);
          setUser(null);
        }
      }

      setIsLoading(false);
    };

    validateToken();
  }, []);

  const login = async () => {
    try {
      // Get authorization URL from backend
      const response = await axios.get(`${API_URL}/auth/login`);
      const { auth_url, state } = response.data;

      // Store state for validation
      sessionStorage.setItem('oauth_state', state);

      // Redirect to Microsoft login
      window.location.href = auth_url;
    } catch (error) {
      console.error('Login failed:', error);
      throw error;
    }
  };

  const handleCallback = async (code: string, state: string) => {
    try {
      // Verify state to prevent CSRF
      const storedState = sessionStorage.getItem('oauth_state');
      if (state !== storedState) {
        throw new Error('Invalid state parameter - possible CSRF attack');
      }

      // Exchange authorization code for tokens
      const response = await axios.post(`${API_URL}/auth/callback`, {
        code,
        state,
      });

      const { access_token, user: userData } = response.data;

      // Store token and user data
      localStorage.setItem('access_token', access_token);
      setAccessToken(access_token);
      setUser(userData);

      // Clean up state
      sessionStorage.removeItem('oauth_state');
    } catch (error) {
      console.error('OAuth callback failed:', error);
      throw error;
    }
  };

  const logout = () => {
    // Clear token from storage
    localStorage.removeItem('access_token');
    setAccessToken(null);
    setUser(null);

    // Optional: Call backend logout endpoint
    if (accessToken) {
      axios.post(`${API_URL}/auth/logout`, {}, {
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      }).catch(err => {
        console.error('Logout endpoint failed:', err);
        // Continue with local logout anyway
      });
    }
  };

  const value: AuthContextType = {
    user,
    accessToken,
    isAuthenticated: !!accessToken,
    isLoading,
    login,
    logout,
    handleCallback,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
