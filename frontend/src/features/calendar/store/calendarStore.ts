import { create } from 'zustand';
import type { Task } from '../types/calendar.types';
import { getCurrentWeekStart, getWeekStart, getWeekIdFromDate } from '../utils/dateHelpers';
import { parseTimeString } from '../utils/timeCalculations';
import { fetchWeekEvents } from '../api/calendarApi';
import { transformCalendarEventToTask } from '../utils/eventTransform';

interface CalendarPatch {
  patch_id: string;
  op: 'add_event' | 'remove_event' | 'modify_event' | 'move_event';
  target_day: {
    scheduled_date: string;
    anchor: any;
  };
  complete_event?: {
    id?: string;
    title: string;
    date: string;
    start_time: string;
    end_time: string;
  };
  [key: string]: any;
}

interface CalendarStore {
  currentWeekStart: Date;
  tasks: Task[];
  previousTasks: Task[] | null;
  hasPendingChanges: boolean;
  isLoading: boolean;
  error: string | null;
  proposedPatches: CalendarPatch[];
  highlightedTaskIds: Set<string>;

  // Actions
  setCurrentWeekStart: (date: Date) => void;
  nextWeek: () => void;
  previousWeek: () => void;
  setTasks: (tasks: Task[]) => void;
  loadWeekEvents: (weekId: string) => Promise<void>;
  loadMockData: () => void;
  addTask: (task: Task) => void;
  removeTask: (taskId: string) => void;
  setProposedPatches: (patches: CalendarPatch[]) => void;
  clearProposedPatches: () => void;
  revertChanges: () => void;
  commitChanges: () => void;
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

// Helper function to apply patches to tasks array
function applyPatchesToTasks(tasks: Task[], patches: CalendarPatch[], currentWeekStart: Date): Task[] {
  let updatedTasks = [...tasks];

  patches.forEach(patch => {
    if (patch.op === 'add_event' && patch.complete_event) {
      // Add new event
      const dayOfWeek = new Date(patch.complete_event.date).getDay();
      const startTime = parseTimeString(patch.complete_event.start_time, new Date(patch.complete_event.date));
      const endTime = parseTimeString(patch.complete_event.end_time, new Date(patch.complete_event.date));

      const newTask: Task = {
        id: patch.patch_id, // Use patch_id as temporary ID
        title: patch.complete_event.title,
        description: patch.complete_event.description || '',
        startTime,
        endTime,
        dayOfWeek
      };

      updatedTasks.push(newTask);
      console.log('[calendarStore] Applied add_event patch:', newTask.title);
    }
    else if (patch.op === 'remove_event') {
      // Remove event by matching date and time
      const patchDate = patch.target_day.scheduled_date;
      updatedTasks = updatedTasks.filter(task => {
        const taskDate = task.startTime.toISOString().split('T')[0];
        return taskDate !== patchDate;
      });
      console.log('[calendarStore] Applied remove_event patch for date:', patchDate);
    }
    else if (patch.op === 'modify_event' && patch.complete_event) {
      // Modify existing event
      updatedTasks = updatedTasks.map(task => {
        const taskDate = task.startTime.toISOString().split('T')[0];
        const patchDate = patch.complete_event?.date || patch.target_day.scheduled_date;

        if (taskDate === patchDate) {
          return {
            ...task,
            title: patch.complete_event?.title || task.title,
            description: patch.complete_event?.description || task.description,
          };
        }
        return task;
      });
      console.log('[calendarStore] Applied modify_event patch');
    }
    else if (patch.op === 'move_event' && patch.complete_event) {
      // Move event to new date/time
      updatedTasks = updatedTasks.map(task => {
        const taskDate = task.startTime.toISOString().split('T')[0];
        const fromDate = patch.from_day?.scheduled_date;

        if (taskDate === fromDate) {
          const newDayOfWeek = new Date(patch.complete_event.date).getDay();
          const newStartTime = parseTimeString(patch.complete_event.start_time, new Date(patch.complete_event.date));
          const newEndTime = parseTimeString(patch.complete_event.end_time, new Date(patch.complete_event.date));

          return {
            ...task,
            dayOfWeek: newDayOfWeek,
            startTime: newStartTime,
            endTime: newEndTime,
          };
        }
        return task;
      });
      console.log('[calendarStore] Applied move_event patch');
    }
  });

  return updatedTasks;
}

export const useCalendarStore = create<CalendarStore>((set, get) => ({
  currentWeekStart: getCurrentWeekStart(),
  tasks: [],
  previousTasks: null,
  hasPendingChanges: false,
  isLoading: false,
  error: null,
  proposedPatches: [],
  highlightedTaskIds: new Set<string>(),

  setCurrentWeekStart: (date: Date) => {
    const weekStart = getWeekStart(date);
    set({ currentWeekStart: weekStart });
  },

  nextWeek: () => {
    const { currentWeekStart, loadWeekEvents } = get();
    const nextWeek = new Date(currentWeekStart);
    nextWeek.setDate(currentWeekStart.getDate() + 7);
    set({ currentWeekStart: nextWeek });

    // Load events for new week
    const weekId = getWeekIdFromDate(nextWeek);
    loadWeekEvents(weekId);
  },

  previousWeek: () => {
    const { currentWeekStart, loadWeekEvents } = get();
    const prevWeek = new Date(currentWeekStart);
    prevWeek.setDate(currentWeekStart.getDate() - 7);
    set({ currentWeekStart: prevWeek });

    // Load events for new week
    const weekId = getWeekIdFromDate(prevWeek);
    loadWeekEvents(weekId);
  },

  setTasks: (tasks: Task[]) => {
    set({ tasks });
  },

  loadWeekEvents: async (weekId: string) => {
    set({ isLoading: true, error: null });
    try {
      console.log('[calendarStore] Loading events for week:', weekId);
      const events = await fetchWeekEvents(weekId);

      // Transform events to tasks
      const { currentWeekStart } = get();
      const tasks = events.map(event =>
        transformCalendarEventToTask(event, currentWeekStart)
      );

      console.log('[calendarStore] Loaded', tasks.length, 'tasks');
      set({ tasks, isLoading: false });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to load events';
      console.error('[calendarStore] Error loading events:', errorMessage);
      set({
        error: errorMessage,
        isLoading: false,
        tasks: [], // Clear tasks on error
      });
    }
  },

  // Mock data loader - kept for testing, not used in production
  loadMockData: () => {
    console.warn('[calendarStore] Loading mock data (testing only)');
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
  },

  setProposedPatches: (patches: CalendarPatch[]) => {
    const { tasks, currentWeekStart } = get();

    // Save current state before applying changes
    const previousTasks = [...tasks];

    // Apply patches immediately to tasks
    const updatedTasks = applyPatchesToTasks(tasks, patches, currentWeekStart);

    // Derive highlighted task IDs (for newly added tasks, use patch_id)
    const highlighted = new Set<string>();
    patches.forEach(patch => {
      if (patch.op === 'add_event') {
        highlighted.add(patch.patch_id); // Highlight the new task
      } else if (patch.complete_event?.id) {
        highlighted.add(patch.complete_event.id);
      }
    });

    console.log('[calendarStore] Auto-applying', patches.length, 'patches, highlighting', highlighted.size, 'tasks');
    set({
      tasks: updatedTasks,
      previousTasks,
      proposedPatches: patches,
      highlightedTaskIds: highlighted,
      hasPendingChanges: true
    });
  },

  clearProposedPatches: () => {
    console.log('[calendarStore] Clearing proposed patches');
    set({ proposedPatches: [], highlightedTaskIds: new Set<string>() });
  },

  revertChanges: () => {
    const { previousTasks } = get();
    if (previousTasks) {
      console.log('[calendarStore] Reverting to previous state');
      set({
        tasks: previousTasks,
        previousTasks: null,
        proposedPatches: [],
        highlightedTaskIds: new Set<string>(),
        hasPendingChanges: false
      });
    }
  },

  commitChanges: () => {
    console.log('[calendarStore] Committing changes');
    set({
      previousTasks: null,
      proposedPatches: [],
      highlightedTaskIds: new Set<string>(),
      hasPendingChanges: false
    });
  }
}));
