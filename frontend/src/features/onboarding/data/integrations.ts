export interface Integration {
  id: string;
  name: string;
  description: string;
  icon: string;
}

export type { Integration };

export const integrations: Integration[] = [
  {
    id: 'github',
    name: 'Github',
    description:
      'Ultra learns how you build — your coding rhythm, focus patterns, and project progress — to schedule deep work at your creative peak.',
    icon: 'http://localhost:3845/assets/0843646223c06b70058ec5b4a5858020f010e956.png',
  },
  {
    id: 'whoop',
    name: 'Whoop',
    description:
      'Ultra listens to your body — your recovery, strain, and readiness — to align your energy with your goals.',
    icon: 'http://localhost:3845/assets/f5d4c0238aec3e927e45746e16e1a1721415023a.png',
  },
  {
    id: 'trayne',
    name: 'Trayne',
    description:
      'Ultra connects to your training engine — syncing your workouts, recovery data, and performance insights. Your training plan automatically adapts based on your health, readiness, and daily rhythm.',
    icon: 'http://localhost:3845/assets/f852e1882f84f2e208dd8a4d0ac2cf3f2f411dfd.svg',
  },
  {
    id: 'linear',
    name: 'Linear',
    description:
      'Ultra syncs with your project workflow — tracking issues, milestones, and sprint velocity — to optimize when you tackle deep technical work.',
    icon: 'https://api.iconify.design/simple-icons:linear.svg?color=%23ffffff',
  },
];
