import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import {
  confirmSignIn,
  confirmSignUp,
  fetchAuthSession,
  getCurrentUser,
  resendSignUpCode,
  signIn,
  signOut,
  signUp
} from 'aws-amplify/auth';
import { authConfigured, config } from '../config';

const AuthContext = createContext(null);

const MOCK_USER_KEY = 'aussie-ecolens-mock-user';

const getTokenPayload = async () => {
  const session = await fetchAuthSession();
  return session.tokens?.idToken?.payload || session.tokens?.accessToken?.payload || {};
};

export function AuthProvider({ children }) {
  const mockAuth = config.useMocks || !authConfigured;
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [pendingUsername, setPendingUsername] = useState('');

  const refreshUser = useCallback(async () => {
    setLoading(true);
    try {
      if (mockAuth) {
        const stored = localStorage.getItem(MOCK_USER_KEY);
        setUser(stored ? JSON.parse(stored) : null);
        return;
      }

      const current = await getCurrentUser();
      const payload = await getTokenPayload();
      setUser({
        username: current.username,
        email: payload.email || current.signInDetails?.loginId || current.username,
        givenName: payload.given_name || '',
        familyName: payload.family_name || ''
      });
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, [mockAuth]);

  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  const login = useCallback(
    async ({ email, password }) => {
      if (mockAuth) {
        const mockUser = {
          username: email,
          email,
          givenName: 'Chenhuan',
          familyName: 'Wang'
        };
        localStorage.setItem(MOCK_USER_KEY, JSON.stringify(mockUser));
        setUser(mockUser);
        return { isSignedIn: true, nextStep: { signInStep: 'DONE' } };
      }

      const result = await signIn({ username: email, password });
      setPendingUsername(email);
      if (result.isSignedIn) {
        await refreshUser();
      }
      return result;
    },
    [mockAuth, refreshUser]
  );

  const register = useCallback(
    async ({ email, password, givenName, familyName }) => {
      if (mockAuth) {
        setPendingUsername(email);
        return { nextStep: { signUpStep: 'CONFIRM_SIGN_UP' } };
      }

      setPendingUsername(email);
      return signUp({
        username: email,
        password,
        options: {
          userAttributes: {
            email,
            given_name: givenName,
            family_name: familyName
          }
        }
      });
    },
    [mockAuth]
  );

  const verifyEmail = useCallback(
    async ({ email, code }) => {
      if (mockAuth) {
        return { isSignUpComplete: true };
      }
      return confirmSignUp({ username: email, confirmationCode: code });
    },
    [mockAuth]
  );

  const resendCode = useCallback(
    async (email) => {
      if (mockAuth) {
        return true;
      }
      return resendSignUpCode({ username: email });
    },
    [mockAuth]
  );

  const completeNewPassword = useCallback(
    async (newPassword) => {
      if (mockAuth) {
        await refreshUser();
        return { isSignedIn: true };
      }
      const result = await confirmSignIn({ challengeResponse: newPassword });
      if (result.isSignedIn) {
        await refreshUser();
      }
      return result;
    },
    [mockAuth, refreshUser]
  );

  const logout = useCallback(async () => {
    if (mockAuth) {
      localStorage.removeItem(MOCK_USER_KEY);
      setUser(null);
      return;
    }
    await signOut();
    setUser(null);
  }, [mockAuth]);

  const value = useMemo(
    () => ({
      user,
      loading,
      mockAuth,
      pendingUsername,
      login,
      register,
      verifyEmail,
      resendCode,
      completeNewPassword,
      logout,
      refreshUser
    }),
    [
      user,
      loading,
      mockAuth,
      pendingUsername,
      login,
      register,
      verifyEmail,
      resendCode,
      completeNewPassword,
      logout,
      refreshUser
    ]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export const useAuth = () => useContext(AuthContext);

