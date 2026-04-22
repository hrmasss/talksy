import { createContext, useContext } from "react";

interface OnboardingGateContextValue {
  requireOnboarding: () => boolean;
}

export const OnboardingGateContext = createContext<OnboardingGateContextValue | null>(null);

export function useOnboardingGate() {
  const ctx = useContext(OnboardingGateContext);
  if (!ctx) {
    throw new Error("useOnboardingGate must be used within AppLayout");
  }
  return ctx;
}
