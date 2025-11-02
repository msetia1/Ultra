import { create } from 'zustand';
import type { Task, WeekData } from '../types/calendar.types';
import { getCurrentWeekStart, getWeekEnd, getWeekStart } from '../utils/dateHelpers';
import { parseTimeString } from '../utils/timeCalculations';

interface CalendarStore {
  currentWeekStart: Date;
  tasks: Task[];
  isLoading: boolean;
  error: string | null;

  // Actions
  setCurrentWeekStart: (date: Date) => void;
  nextWeek: () => void;
  previousWeek: () => void;
  loadMockData: () => void;
  addTask: (task: Task) => void;
  removeTask: (taskId: string) => void;
}

// Mock data generator for testing
function generateMockTasks(): Task[] {
  const weekStart = getCurrentWeekStart();
  const tasks: Task[] = [];

  // Task templates with varied times and durations
  const taskTemplates = [
    { time: '8:00 AM', duration: 1, title: 'Morning Standup', description: 'Quick team sync to discuss today\'s priorities and blockers' },
    { time: '10:00 AM', duration: 2, title: 'Deep Work', description: 'Focused coding session on high-priority features without interruptions' },
    { time: '1:00 PM', duration: 1, title: 'Lunch & Learn', description: 'Informal team discussion about latest technologies and best practices' },
    { time: '3:00 PM', duration: 2, title: 'Deep Work', description: 'Focused coding session on high-priority features without interruptions' },
    { time: '5:00 PM', duration: 1, title: 'Code Review', description: 'Review team pull requests and provide constructive feedback' },
    { time: '7:00 PM', duration: 2, title: 'Evening Session', description: 'Work on personal projects and explore new technologies' },
  ];

  // Generate varied tasks throughout the week
  for (let day = 0; day < 7; day++) {
    const currentDate = new Date(weekStart);
    currentDate.setDate(weekStart.getDate() + day);

    // Add 1-3 tasks per day with varied timing
    const numTasks = Math.floor(Math.random() * 3) + 1;
    const usedTemplates = new Set<number>();

    for (let i = 0; i < numTasks; i++) {
      // Pick a random template that hasn't been used today
      let templateIndex;
      do {
        templateIndex = Math.floor(Math.random() * taskTemplates.length);
      } while (usedTemplates.has(templateIndex));

      usedTemplates.add(templateIndex);
      const template = taskTemplates[templateIndex];

      const startTime = parseTimeString(template.time, currentDate);
      const endTime = new Date(startTime);
      endTime.setHours(endTime.getHours() + template.duration);

      tasks.push({
        id: `task-${day}-${i}`,
        title: template.title,
        description: template.description,
        startTime,
        endTime,
        dayOfWeek: day
      });
    }
  }

  return tasks;
}

export const useCalendarStore = create<CalendarStore>((set, get) => ({
  currentWeekStart: getCurrentWeekStart(),
  tasks: [],
  isLoading: false,
  error: null,

  setCurrentWeekStart: (date: Date) => {
    const weekStart = getWeekStart(date);
    set({ currentWeekStart: weekStart });
  },

  nextWeek: () => {
    const { currentWeekStart } = get();
    const nextWeek = new Date(currentWeekStart);
    nextWeek.setDate(currentWeekStart.getDate() + 7);
    set({ currentWeekStart: nextWeek });
  },

  previousWeek: () => {
    const { currentWeekStart } = get();
    const prevWeek = new Date(currentWeekStart);
    prevWeek.setDate(currentWeekStart.getDate() - 7);
    set({ currentWeekStart: prevWeek });
  },

  loadMockData: () => {
    set({ isLoading: true, error: null });
    try {
      const mockTasks = generateMockTasks();
      set({ tasks: mockTasks, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to load tasks',
        isLoading: false
      });
    }
  },

  addTask: (task: Task) => {
    set((state) => ({
      tasks: [...state.tasks, task]
    }));
  },

  removeTask: (taskId: string) => {
    set((state) => ({
      tasks: state.tasks.filter((task) => task.id !== taskId)
    }));
  }
}));
