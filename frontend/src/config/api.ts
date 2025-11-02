/**
 * API Configuration
 *
 * In production, frontend and backend are served from the same origin,
 * so we use relative URLs (empty base URL).
 *
 * In development, you can set VITE_API_URL to point to your backend server.
 */

export const API_BASE_URL = import.meta.env.VITE_API_URL || '';

export const API_ENDPOINTS = {
  // WHOOP
  whoopStart: `${API_BASE_URL}/auth/whoop/start`,
  whoopCallback: `${API_BASE_URL}/auth/whoop/callback`,
  whoopCycles: `${API_BASE_URL}/whoop/cycles`,

  // GitHub
  githubConnect: `${API_BASE_URL}/auth/github/connect`,
  githubRepositories: `${API_BASE_URL}/github/repositories`,
  githubBackfill: `${API_BASE_URL}/github/backfill`,

  // Linear
  linearStart: `${API_BASE_URL}/auth/linear/start`,
  linearCallback: `${API_BASE_URL}/auth/linear/callback`,
  linearTeams: `${API_BASE_URL}/linear/teams`,
  linearIssues: `${API_BASE_URL}/linear/issues`,
  linearProjects: `${API_BASE_URL}/linear/projects`,

  // General
  health: `${API_BASE_URL}/health`,
  api: `${API_BASE_URL}/api`,
} as const;
