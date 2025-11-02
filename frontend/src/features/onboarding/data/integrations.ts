export interface Integration {
  id: string;
  name: string;
  description: string;
  icon: string;
}

export const integrations: Integration[] = [
  {
    id: 'github',
    name: 'Github',
    description:
      'Ultra learns how you build — your coding rhythm, focus patterns, and project progress — to schedule deep work at your creative peak.',
    icon: '/icons/github.png',
  },
  {
    id: 'whoop',
    name: 'Whoop',
    description:
      'Ultra listens to your body — your recovery, strain, and readiness — to align your energy with your goals.',
    icon: '/icons/whoop.png',
  },
  {
    id: 'trayne',
    name: 'Trayne',
    description:
      'Ultra connects to your training engine — syncing your workouts, recovery data, and performance insights. Your training plan automatically adapts based on your health, readiness, and daily rhythm.',
    icon: '/icons/trayne.svg',
  },
  {
    id: 'linear',
    name: 'Linear',
    description:
      'Ultra syncs with your project workflow — tracking issues, milestones, and sprint velocity — to optimize when you tackle deep technical work.',
    icon: '/icons/linear.svg',
  },
];
