/**
 * AuthContext - Global authentication state management
 *
 * Stores JWT token in localStorage and exposes:
 * - user info (decoded from JWT)
 * - driveToken (for Google Drive API calls)
 * - login/logout methods
 */

import React, { createContext, useState, useContext, useEffect } from 'react';
import { jwtDecode } from 'jwt-decode';

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
      } catch (error) {
        console.error('Failed to decode token:', error);
        localStorage.removeItem('auth_token');
      }
    }
    setLoading(false);
  }, []);

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
    logout
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
