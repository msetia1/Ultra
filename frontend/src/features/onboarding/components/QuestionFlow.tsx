import { useState } from 'react';
import QuestionScreen from './QuestionScreen';
import { useOnboardingStore } from '../store/onboardingStore';

interface Question {
  id: string;
  text: string;
  storeField: 'values' | 'goals' | 'projects';
  updateAction: 'updateValues' | 'updateGoals' | 'updateProjects';
}

const questions: Question[] = [
  {
    id: 'values',
    text: 'What are your values?',
    storeField: 'values',
    updateAction: 'updateValues',
  },
  {
    id: 'goals',
    text: 'What are you goals?',
    storeField: 'goals',
    updateAction: 'updateGoals',
  },
  {
    id: 'projects',
    text: 'What projects are you working on?',
    storeField: 'projects',
    updateAction: 'updateProjects',
  },
];

export default function QuestionFlow() {
  const [localQuestionIndex, setLocalQuestionIndex] = useState(0);

  const {
    values,
    goals,
    projects,
    updateValues,
    updateGoals,
    updateProjects,
    setCurrentStep,
    previousStep,
  } = useOnboardingStore();

  const currentQuestion = questions[localQuestionIndex];

  // Get the current value from the store
  const getCurrentValue = () => {
    switch (currentQuestion.storeField) {
      case 'values':
        return values;
      case 'goals':
        return goals;
      case 'projects':
        return projects;
      default:
        return '';
    }
  };

  // Update the store with the new value
  const handleChange = (value: string) => {
    switch (currentQuestion.updateAction) {
      case 'updateValues':
        updateValues(value);
        break;
      case 'updateGoals':
        updateGoals(value);
        break;
      case 'updateProjects':
        updateProjects(value);
        break;
    }
  };

  const handleNext = () => {
    if (localQuestionIndex < questions.length - 1) {
      // Move to next question
      setLocalQuestionIndex(localQuestionIndex + 1);
    } else {
      // Completed all questions, move to next onboarding step
      setCurrentStep(8);
    }
  };

  const handleBack = () => {
    if (localQuestionIndex > 0) {
      // Go back to previous question
      setLocalQuestionIndex(localQuestionIndex - 1);
    } else {
      // Go back to the carousel (previous onboarding step)
      previousStep();
    }
  };

  return (
    <QuestionScreen
      question={currentQuestion.text}
      value={getCurrentValue()}
      onChange={handleChange}
      onNext={handleNext}
      onBack={handleBack}
      canGoBack={true}
    />
  );
}
