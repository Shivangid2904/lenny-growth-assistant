import { useState, useEffect } from 'react';
import { createSession, getSession, ApiError } from '../lib/api';
import { SessionDetail } from '../types/api';

export function useSession() {
  const [session, setSession] = useState<SessionDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    initializeSession();
  }, []);

  const initializeSession = async () => {
    try {
      setIsLoading(true);
      setError(null);
      
      // Try to get existing session from localStorage
      const savedSessionId = localStorage.getItem('lenny_session_id');
      if (savedSessionId) {
        try {
          const existingSession = await getSession(savedSessionId);
          setSession(existingSession);
          return;
        } catch (err) {
          if (err instanceof ApiError && err.statusCode === 404) {
            // Session not found, create new one
            localStorage.removeItem('lenny_session_id');
          } else {
            throw err;
          }
        }
      }

      // Create new session
      const newSession = await createSession();
      const sessionDetail = await getSession(newSession.id);
      setSession(sessionDetail);
      localStorage.setItem('lenny_session_id', newSession.id);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError('Failed to initialize session');
      }
    } finally {
      setIsLoading(false);
    }
  };

  return { session, isLoading, error, refreshSession: initializeSession };
}
