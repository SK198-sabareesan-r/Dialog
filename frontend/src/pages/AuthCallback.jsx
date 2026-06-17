/**
 * AuthCallback - OAuth popup handler
 *
 * This page handles the OAuth redirect in a popup window.
 * It extracts the authorization code, exchanges it for a JWT,
 * and sends the token back to the parent window via postMessage.
 */

import React, { useEffect, useState } from 'react';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const FRONTEND_URL = process.env.REACT_APP_FRONTEND_URL || 'http://localhost:3000';

function AuthCallback() {
  const [status, setStatus] = useState('Processing...');
  const [error, setError] = useState(null);

  useEffect(() => {
    const handleCallback = async () => {
      try {
        // Check if already processed (React StrictMode causes double render)
        const exchanged = sessionStorage.getItem('oauth_exchanged');
        if (exchanged) {
          setStatus('Already processed');
          return;
        }

        // Extract code and state from URL
        const params = new URLSearchParams(window.location.search);
        const code = params.get('code');
        const state = params.get('state');
        const errorParam = params.get('error');

        // Handle OAuth error
        if (errorParam) {
          const errorDescription = params.get('error_description') || 'OAuth failed';
          throw new Error(errorDescription);
        }

        if (!code || !state) {
          throw new Error('Missing authorization code or state');
        }

        // Mark as exchanged to prevent double processing
        sessionStorage.setItem('oauth_exchanged', 'true');

        setStatus('Exchanging code for token...');

        // Exchange authorization code for JWT token
        const response = await fetch(
          `${API_BASE_URL}/api/auth/callback?code=${encodeURIComponent(code)}&state=${encodeURIComponent(state)}`
        );

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.detail || 'Authentication failed');
        }

        const data = await response.json();

        if (!data.token) {
          throw new Error('No token received from server');
        }

        setStatus('Authentication successful!');

        // Send token to parent window
        if (window.opener) {
          window.opener.postMessage(
            {
              type: 'GOOGLE_AUTH_SUCCESS',
              token: data.token,
              user: data.user
            },
            FRONTEND_URL
          );

          // Close popup after short delay
          setTimeout(() => {
            window.close();
          }, 1000);
        } else {
          throw new Error('Parent window not found');
        }

      } catch (err) {
        console.error('OAuth callback error:', err);
        setError(err.message);
        setStatus('Authentication failed');

        // Send error to parent window
        if (window.opener) {
          window.opener.postMessage(
            {
              type: 'GOOGLE_AUTH_ERROR',
              message: err.message
            },
            FRONTEND_URL
          );

          setTimeout(() => {
            window.close();
          }, 3000);
        }
      }
    };

    handleCallback();
  }, []);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-purple-400 via-pink-500 to-orange-400">
      <div className="bg-white rounded-2xl shadow-2xl p-12 max-w-md w-full text-center">
        {/* Dialog Logo */}
        <div className="flex justify-center mb-6">
          <img
            src="https://dialog.lk/themes/custom/dialog_theme/logo.svg"
            alt="Dialog"
            className="h-10"
          />
        </div>

        {/* Status */}
        <div className="mb-4">
          {!error ? (
            <div className="flex justify-center mb-4">
              <svg className="animate-spin h-12 w-12 text-pink-500" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
            </div>
          ) : (
            <div className="flex justify-center mb-4">
              <svg className="h-12 w-12 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
          )}

          <h2 className="text-xl font-semibold text-gray-800 mb-2">
            {status}
          </h2>

          {error && (
            <p className="text-red-600 text-sm mt-4">
              {error}
            </p>
          )}

          {!error && (
            <p className="text-gray-600 text-sm">
              This window will close automatically...
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

export default AuthCallback;
