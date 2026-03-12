import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  clearAuthSession,
  getCurrentUser,
  getStoredUser,
  loginRequest,
  persistAuthSession,
  setStoredUser,
  signupRequest,
  type SignupPayload,
  type User,
} from "./auth-api";
import { getStoredAccessToken } from "./api-client";

interface AuthContextValue {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<User>;
  signup: (payload: SignupPayload) => Promise<void>;
  logout: () => void;
  setUser: (user: User | null) => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUserState] = useState<User | null>(() => getStoredUser());
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function bootstrapAuth() {
      const accessToken = getStoredAccessToken();
      const storedUser = getStoredUser();

      if (!accessToken) {
        clearAuthSession();
        if (!cancelled) {
          setUserState(null);
          setIsLoading(false);
        }
        return;
      }

      if (storedUser) {
        setUserState(storedUser);
      }

      try {
        const currentUser = await getCurrentUser();
        if (!cancelled) {
          setStoredUser(currentUser);
          setUserState(currentUser);
        }
      } catch {
        clearAuthSession();
        if (!cancelled) {
          setUserState(null);
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    void bootstrapAuth();

    return () => {
      cancelled = true;
    };
  }, []);

  function setUser(userValue: User | null): void {
    setStoredUser(userValue);
    setUserState(userValue);
  }

  async function login(email: string, password: string): Promise<User> {
    const response = await loginRequest({ email, password });
    persistAuthSession(response);
    setUserState(response.user);
    return response.user;
  }

  async function signup(payload: SignupPayload): Promise<void> {
    const response = await signupRequest(payload);
    persistAuthSession(response);
    setUserState(response.user);
  }

  function logout(): void {
    clearAuthSession();
    setUserState(null);
  }

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isAuthenticated: user != null,
      isLoading,
      login,
      signup,
      logout,
      setUser,
    }),
    [isLoading, user]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }

  return context;
}
