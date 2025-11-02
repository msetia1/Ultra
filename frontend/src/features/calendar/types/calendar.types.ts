export interface Task {
  id: string;
  title: string;
  description: string;
  startTime: Date;
  endTime: Date;
  dayOfWeek: number; // 0=Monday, 6=Sunday
}

export interface WeekData {
  startDate: Date;
  endDate: Date;
  tasks: Task[];
}

export interface CalendarState {
  currentWeek: WeekData | null;
  isLoading: boolean;
  error: string | null;
}
