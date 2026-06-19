/**
 * AuthContext - Global authentication state management
 *
 * Stores JWT token in localStorage and exposes:
 * - user info (decoded from JWT)
 * - driveToken (for Google Drive API calls)
 * - login/logout methods
 */

import React, { createContext, useState, useContext, useEffect, useCallback } from 'react';
import { jwtDecode } from 'jwt-decode';
import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8001';

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [driveToken, setDriveToken] = useState(null);
  const [loading, setLoading] = useState(true);

  const refreshDriveToken = useCallback(async (currentJwt) => {
    try {
      const res = await axios.post(`${API_BASE}/api/auth/refresh-drive-token`, {
        jwt_token: currentJwt || localStorage.getItem('auth_token'),
      });
      const newJwt = res.data.token;
      localStorage.setItem('auth_token', newJwt);
      setToken(newJwt);
      setDriveToken(res.data.drive_token);
      return res.data.drive_token;
    } catch (err) {
      console.warn('Drive token refresh failed:', err);
      return null;
    }
  }, []);

  // Load token from localStorage on mount
  useEffect(() => {
    const storedToken = localStorage.getItem('auth_token');
    if (storedToken) {
      try {
        const decoded = jwtDecode(storedToken);

        // Check if token is expired
        const now = Date.now() / 1000;
        if (decoded.exp && decoded.exp < now) {
          // Token expired - clear it
          localStorage.removeItem('auth_token');
          setLoading(false);
          return;
        }

        // Token valid - restore session
        setToken(storedToken);
        setUser({
          id: decoded.sub,
          email: decoded.email,
          name: decoded.name,
          picture: decoded.picture
        });
        setDriveToken(decoded.drive_token);
        // Check if drive token will expire soon (within 5 min) and refresh proactively
        if (decoded.drive_refresh_token) {
          const driveExpiry = decoded.iat + 3600; // Google tokens expire in 1h
          const now = Date.now() / 1000;
          if (driveExpiry - now < 300) {
            // Will refresh silently in background
            setTimeout(() => refreshDriveToken(storedToken), 100);
          }
        }
      } catch (error) {
        console.error('Failed to decode token:', error);
        localStorage.removeItem('auth_token');
      }
    }
    setLoading(false);
  }, [refreshDriveToken]);

  const login = (jwtToken) => {
    try {
      const decoded = jwtDecode(jwtToken);

      // Store token
      localStorage.setItem('auth_token', jwtToken);
      setToken(jwtToken);

      // Extract user info
      setUser({
        id: decoded.sub,
        email: decoded.email,
        name: decoded.name,
        picture: decoded.picture
      });

      // Extract Drive token
      setDriveToken(decoded.drive_token);

      return true;
    } catch (error) {
      console.error('Login failed:', error);
      return false;
    }
  };

  const logout = () => {
    localStorage.removeItem('auth_token');
    setToken(null);
    setUser(null);
    setDriveToken(null);
  };

  const value = {
    user,
    token,
    driveToken,
    isAuthenticated: !!user,
    loading,
    login,
    logout,
    refreshDriveToken,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
