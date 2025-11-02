export interface WelcomeScreenData {
  lines: string[];
  isItalic: boolean;
}

export const welcomeScreens: WelcomeScreenData[] = [
  {
    lines: [
      "Focus is a state.",
      "Ultra helps you live it."
    ],
    isItalic: false
  },
  {
    lines: [
      "It listens to your body.",
      "It learns from your code.",
      "It aligns with your goals."
    ],
    isItalic: false
  },
  {
    lines: [
      "Ultra evolves with every commit,",
      "every night of rest, every win."
    ],
    isItalic: false
  },
  {
    lines: [
      "This is beyond scheduling.",
      "This is Ultra."
    ],
    isItalic: false
  },
  {
    lines: [
      "Enter the Ultra state."
    ],
    isItalic: true
  }
];
