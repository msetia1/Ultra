/**
 * Helper functions for week generation
 */

import { getWeekIdFromDate } from './dateHelpers';

/**
 * Get current week ID in format expected by backend API
 * Example: "2025-W09"
 */
export function getCurrentWeekId(): string {
  return getWeekIdFromDate(new Date());
}

/**
 * Build generation request from onboarding data
 * Combines user's goals, values, and projects into a coherent request
 */
export function buildGenerationRequest(onboardingData: {
  goals: string;
  values: string;
  projects: string;
}): { user_goals: string; user_context: Record<string, any> } {
  // Combine user input into comprehensive goals statement
  const goalsParts: string[] = [];

  if (onboardingData.goals) {
    goalsParts.push(onboardingData.goals);
  }

  if (onboardingData.values) {
    goalsParts.push(`Values: ${onboardingData.values}`);
  }

  if (onboardingData.projects) {
    goalsParts.push(`Projects: ${onboardingData.projects}`);
  }

  // Fallback to default if no onboarding data
  const user_goals = goalsParts.length > 0
    ? goalsParts.join('. ')
    : 'productivity and work-life balance';

  console.log('[generationHelpers] Built user goals:', user_goals);

  return {
    user_goals,
    user_context: {
      // Placeholder for future integration data
      has_whoop: false,
      has_github: false,
      has_linear: false,
    },
  };
}
