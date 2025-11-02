const FALLBACK_API_BASE_URL = 'http://localhost:8000';

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, '') ?? FALLBACK_API_BASE_URL;

export const ONBOARDING_RETURN_KEY = 'onboarding-return-path';

const withOnboardingReturnHint = () => {
  try {
    localStorage.setItem(ONBOARDING_RETURN_KEY, '/onboarding');
  } catch {
    // no-op: localStorage may be unavailable (SSR/tests)
  }
};

export function startWhoopOAuth(): void {
  withOnboardingReturnHint();
  window.location.href = `${API_BASE_URL}/auth/whoop/start`;
}

export function startLinearOAuth(): void {
  withOnboardingReturnHint();
  window.location.href = `${API_BASE_URL}/auth/linear/start`;
}

export function startGithubOAuth(): void {
  withOnboardingReturnHint();
  window.location.href = `${API_BASE_URL}/auth/github/start`;
}

export async function connectGithubWithPat(personalAccessToken: string) {
  const response = await fetch(`${API_BASE_URL}/auth/github/connect`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ personal_access_token: personalAccessToken }),
  });

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = payload?.detail ?? 'Failed to connect GitHub';
    throw new Error(message);
  }

  return payload;
}
