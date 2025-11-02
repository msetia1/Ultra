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

  // Generate 2 tasks per day for the week
  for (let day = 0; day < 7; day++) {
    const currentDate = new Date(weekStart);
    currentDate.setDate(weekStart.getDate() + day);

    // Morning task
    const morningStart = parseTimeString('10:00 AM', currentDate);
    const morningEnd = parseTimeString('2:00 PM', currentDate);

    tasks.push({
      id: `task-${day}-morning`,
      title: 'Deep Work',
      description: 'Complete Morph diffs feature to update calendar super fast.',
      startTime: morningStart,
      endTime: morningEnd,
      dayOfWeek: day
    });

    // Afternoon task (only for some days)
    if (day % 2 === 0) {
      const afternoonStart = parseTimeString('3:00 PM', currentDate);
      const afternoonEnd = parseTimeString('5:00 PM', currentDate);

      tasks.push({
        id: `task-${day}-afternoon`,
        title: 'Deep Work',
        description: 'Complete Morph diffs feature to update calendar super fast.',
        startTime: afternoonStart,
        endTime: afternoonEnd,
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
