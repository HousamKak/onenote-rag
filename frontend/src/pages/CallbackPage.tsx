/**
 * OAuth Callback Page - Handles the redirect from Microsoft OAuth.
 */
import React, { useEffect, useState, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const CallbackPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { handleCallback } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const processingRef = useRef(false)

  useEffect(() => {
    const processCallback = async () => {
      // Prevent multiple executions
      if(processingRef.current){
        console.log('Callback already processing, skipping...');
        return;
      }
      processingRef.current=true;
      const code = searchParams.get('code');
      const state = searchParams.get('state');
      const errorParam = searchParams.get('error');
      const errorDescription = searchParams.get('error_description');

      // Check for OAuth errors
      if (errorParam) {
        setError(errorDescription || 'Authentication failed');
        console.error('OAuth error:', errorParam, errorDescription);
        setTimeout(() => navigate('/login'), 3000);
        return;
      }

      if (!code || !state) {
        setError('Missing authorization code or state');
        setTimeout(() => navigate('/login'), 3000);
        return;
      }

      try {
        await handleCallback(code, state);
        // Redirect to main app
        navigate('/query');
      } catch (err) {
        console.error('Callback processing failed:', err);
        setError('Failed to complete sign in. Please try again.');
        setTimeout(() => navigate('/login'), 3000);
      }
    };

    processCallback();
  }, [searchParams, handleCallback, navigate]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full space-y-8 p-8 bg-white rounded-lg shadow-lg text-center">
        {error ? (
          <>
            <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-red-100">
              <svg
                className="h-6 w-6 text-red-600"
                fill="none"
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path d="M6 18L18 6M6 6l12 12"></path>
              </svg>
            </div>
            <div>
              <h2 className="text-xl font-semibold text-gray-900">Authentication Failed</h2>
              <p className="mt-2 text-sm text-gray-600">{error}</p>
              <p className="mt-4 text-sm text-gray-500">Redirecting to login...</p>
            </div>
          </>
        ) : (
          <>
            <div className="mx-auto flex items-center justify-center h-12 w-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            </div>
            <div>
              <h2 className="text-xl font-semibold text-gray-900">Completing Sign In</h2>
              <p className="mt-2 text-sm text-gray-600">Please wait while we verify your credentials...</p>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default CallbackPage;
