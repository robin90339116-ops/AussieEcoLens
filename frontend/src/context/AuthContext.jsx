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
import { authConfigured } from '../config';

const AuthContext = createContext(null);

const getTokenPayload = async () => {
  const session = await fetchAuthSession();
  return session.tokens?.idToken?.payload || session.tokens?.accessToken?.payload || {};
};

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [pendingUsername, setPendingUsername] = useState('');

  const refreshUser = useCallback(async () => {
    setLoading(true);
    try {
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
  }, []);

  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  const login = useCallback(
    async ({ email, password }) => {
      const result = await signIn({ username: email, password });
      setPendingUsername(email);
      if (result.isSignedIn) {
        await refreshUser();
      }
      return result;
    },
    [refreshUser]
  );

  const register = useCallback(
    async ({ email, password, givenName, familyName }) => {
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
    []
  );

  const verifyEmail = useCallback(
    async ({ email, code }) => confirmSignUp({ username: email, confirmationCode: code }),
    []
  );

  const resendCode = useCallback(async (email) => resendSignUpCode({ username: email }), []);

  const completeNewPassword = useCallback(
    async (newPassword) => {
      const result = await confirmSignIn({ challengeResponse: newPassword });
      if (result.isSignedIn) {
        await refreshUser();
      }
      return result;
    },
    [refreshUser]
  );

  const logout = useCallback(async () => {
    await signOut();
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({
      user,
      loading,
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
