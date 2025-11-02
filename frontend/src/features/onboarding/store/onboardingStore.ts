import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface OnboardingStore {
  // Current step tracking (0-9 for 10 total steps)
  currentStep: number;

  // User data from form steps
  values: string;
  goals: string;
  projects: string;
  connectedIntegrations: string[];

  // Actions
  setCurrentStep: (step: number) => void;
  nextStep: () => void;
  previousStep: () => void;
  updateValues: (values: string) => void;
  updateGoals: (goals: string) => void;
  updateProjects: (projects: string) => void;
  connectIntegration: (id: string) => void;
  disconnectIntegration: (id: string) => void;
  completeOnboarding: () => void;
  reset: () => void;
}

const MAX_STEPS = 10;

export const useOnboardingStore = create<OnboardingStore>()(
  persist(
    (set) => ({
      // Initial state
      currentStep: 0,
      values: '',
      goals: '',
      projects: '',
      connectedIntegrations: [],

      // Step navigation
      setCurrentStep: (step) =>
        set({ currentStep: Math.max(0, Math.min(step, MAX_STEPS - 1)) }),

      nextStep: () =>
        set((state) => {
          const newStep = Math.min(state.currentStep + 1, MAX_STEPS - 1);
          console.log('[onboardingStore] nextStep called - current:', state.currentStep, '→ new:', newStep);
          return { currentStep: newStep };
        }),

      previousStep: () =>
        set((state) => ({
          currentStep: Math.max(state.currentStep - 1, 0)
        })),

      // Data updates
      updateValues: (values) => set({ values }),
      updateGoals: (goals) => set({ goals }),
      updateProjects: (projects) => set({ projects }),

      // Integration management
      connectIntegration: (id) =>
        set((state) => ({
          connectedIntegrations: state.connectedIntegrations.includes(id)
            ? state.connectedIntegrations
            : [...state.connectedIntegrations, id]
        })),

      disconnectIntegration: (id) =>
        set((state) => ({
          connectedIntegrations: state.connectedIntegrations.filter((i) => i !== id)
        })),

      // Complete onboarding
      completeOnboarding: () => set({ currentStep: MAX_STEPS }),

      // Reset state
      reset: () => set({
        currentStep: 0,
        values: '',
        goals: '',
        projects: '',
        connectedIntegrations: []
      })
    }),
    {
      name: 'onboarding-storage',
    }
  )
);
