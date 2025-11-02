# AI Scheduler Frontend Architecture

## 📁 Directory Structure

```
src/
├── features/
│   ├── onboarding/
│   │   ├── components/
│   │   │   ├── OnboardingLayout.tsx       # Wrapper with progress indicator
│   │   │   ├── OnboardingStep.tsx         # Individual step wrapper
│   │   │   ├── WelcomeScreen.tsx          # Screens 1-5 (text/messaging)
│   │   │   ├── QuestionInput.tsx          # Reusable input component
│   │   │   ├── ValuesStep.tsx             # Onboarding 6: "What are you values?"
│   │   │   ├── GoalsStep.tsx              # Onboarding 7: "What are you goals?"
│   │   │   ├── ProjectsStep.tsx           # Onboarding 8: "What projects are you working on?"
│   │   │   ├── IntegrationsStep.tsx       # Onboarding 9: Connect your systems
│   │   │   └── LoadingStep.tsx            # Onboarding 10: Processing/loading state
│   │   ├── hooks/
│   │   │   └── useOnboardingData.ts       # Manage form data
│   │   ├── store/
│   │   │   └── onboardingStore.ts         # Zustand store for onboarding state
│   │   └── pages/
│   │       └── Onboarding.tsx             # Main onboarding orchestrator
│   │
│   ├── integrations/
│   │   ├── components/
│   │   │   ├── IntegrationCard.tsx        # Individual integration item
│   │   │   ├── IntegrationList.tsx        # List of integrations
│   │   │   └── ConnectButton.tsx          # Connect/disconnect action
│   │   ├── store/
│   │   │   └── integrationsStore.ts       # Zustand store for integrations
│   │   └── pages/
│   │       └── Integrations.tsx           # Integrations page
│   │
│   └── scheduler/
│       ├── components/
│       │   ├── Calendar/
│       │   │   ├── CalendarView.tsx       # Main calendar component
│       │   │   ├── CalendarHeader.tsx     # Month/week navigation
│       │   │   ├── DayColumn.tsx          # Individual day view
│       │   │   └── EventCard.tsx          # Event/task card
│       │   ├── Sidebar/
│       │   │   ├── Sidebar.tsx            # Left sidebar
│       │   │   └── FilterControls.tsx     # Filters/controls
│       │   └── TaskDialog.tsx             # Create/edit task modal
│       ├── store/
│       │   └── schedulerStore.ts          # Zustand store for calendar/tasks
│       └── pages/
│           └── Main.tsx                   # Main scheduler view
│
├── components/                             # Shared components
│   ├── ui/                                 # shadcn/ui components
│   │   ├── button.tsx
│   │   ├── input.tsx
│   │   ├── card.tsx
│   │   └── ...
│   └── layouts/
│       └── AppLayout.tsx                   # Main app layout wrapper
│
├── lib/
│   ├── api.ts                              # API client
│   └── utils.ts                            # Utility functions
│
├── types/
│   ├── onboarding.ts                       # Onboarding types
│   ├── integrations.ts                     # Integration types
│   └── scheduler.ts                        # Calendar/task types
│
└── store/
    └── index.ts                            # Root store configuration
```

## 🎯 Implementation Phases

### Phase 1: Onboarding Flow (10 Screens)

**Screens Overview:**
1. **Onboarding 1-5**: Welcome/intro messaging screens
   - Simple text content with "Focus is a state. Ultra helps you live it." type messaging
   - Minimal interaction, just progression

2. **Onboarding 6**: Values Collection
   - Question: "What are you values?"
   - Text input field
   - Back/Next navigation

3. **Onboarding 7**: Goals Collection
   - Question: "What are you goals?"
   - Text input field
   - Back/Next navigation

4. **Onboarding 8**: Projects Collection
   - Question: "What projects are you working on?"
   - Text input field
   - Back/Next navigation

5. **Onboarding 9**: System Integrations
   - Title: "Connect your systems of progress"
   - Integration cards (GitHub, Ultra, Jira)
   - Connect buttons for each
   - Finish button

6. **Onboarding 10**: Loading/Processing
   - Loading animation
   - Processing user data

**Components to Build:**
- `OnboardingLayout` - Progress tracking, step wrapper
- `OnboardingStep` - Individual step container
- `WelcomeScreen` - Reusable for screens 1-5
- `QuestionInput` - Reusable input component for 6-8
- `ValuesStep`, `GoalsStep`, `ProjectsStep` - Form steps
- `IntegrationsStep` - Connection interface
- `LoadingStep` - Processing state

**State Management (Zustand):**
```typescript
interface OnboardingStore {
  currentStep: number;
  values: string;
  goals: string;
  projects: string;
  connectedIntegrations: string[];
  setCurrentStep: (step: number) => void;
  updateValues: (values: string) => void;
  updateGoals: (goals: string) => void;
  updateProjects: (projects: string) => void;
  connectIntegration: (id: string) => void;
  disconnectIntegration: (id: string) => void;
  reset: () => void;
}
```

**Key Features:**
- Multi-step form navigation
- Form validation
- Progress persistence
- Skip/back navigation
- Integration connection handling

---

### Phase 2: Integrations Page

**Layout:**
- Grid of integration cards
- Each card shows:
  - Integration icon/logo
  - Integration name
  - Description
  - Connected/disconnected state
  - Connect/Disconnect button

**Components:**
- `IntegrationCard` - Individual integration with state
- `IntegrationList` - Grid layout container
- `ConnectButton` - Action button with loading states

**State Management (Zustand):**
```typescript
interface IntegrationsStore {
  integrations: Integration[];
  loading: boolean;
  fetchIntegrations: () => Promise<void>;
  connectIntegration: (id: string) => Promise<void>;
  disconnectIntegration: (id: string) => Promise<void>;
}
```

**Integration Types:**
- GitHub
- Jira
- Ultra
- Google Calendar (potential)
- Slack (potential)

---

### Phase 3: Main Scheduler/Calendar View

**Layout Structure:**
- **Left Sidebar**: Menu navigation, filters
- **Main Area**: Calendar view
- **Calendar Types**: Week view, Month view

**Components:**

**Calendar:**
- `CalendarView` - Main grid container
- `CalendarHeader` - Date navigation (< November 3rd 16th >)
- `DayColumn` - Individual day with events
- `EventCard` - Task/event cards in calendar
- `TimeGrid` - Hour markers if needed

**Sidebar:**
- `Sidebar` - Navigation menu
- `FilterControls` - View filters (Projects, Timeline, etc.)

**State Management (Zustand):**
```typescript
interface SchedulerStore {
  events: Event[];
  tasks: Task[];
  selectedDate: Date;
  viewMode: 'week' | 'month';
  filters: FilterOptions;
  setViewMode: (mode: 'week' | 'month') => void;
  setSelectedDate: (date: Date) => void;
  fetchEvents: () => Promise<void>;
  createEvent: (event: Event) => Promise<void>;
  updateEvent: (id: string, event: Partial<Event>) => Promise<void>;
  deleteEvent: (id: string) => Promise<void>;
  updateFilters: (filters: FilterOptions) => void;
}
```

**Key Features:**
- Week/month view toggle
- Date navigation
- Event display
- Task cards
- Filtering system
- Responsive layout

---

## 🔧 Technology Stack

### State Management
- **Zustand** - Lightweight state management
  - Separate stores per feature (onboarding, integrations, scheduler)
  - TypeScript support
  - Minimal boilerplate

### Forms
- **React Hook Form** - Form validation and management
  - Used in onboarding steps
  - Validation schemas with Zod

### Routing
- **React Router** - Navigation
  - Protected routes (require onboarding completion)
  - Routes:
    - `/onboarding` - Onboarding flow
    - `/` - Main scheduler (protected)
    - `/integrations` - Integrations page (protected)

### API Communication
- **Axios** or **Fetch** - HTTP client
  - Centralized in `lib/api.ts`
  - Interceptors for auth
  - Error handling

### UI Components
- **shadcn/ui** - Component library
- **Tailwind CSS** - Styling
- **Lucide React** - Icons

### Additional Libraries (as needed)
- **date-fns** - Date manipulation for calendar
- **react-beautiful-dnd** - Drag and drop (if needed)
- **zod** - Schema validation

---

## 🚀 Implementation Order

1. **Setup Zustand stores** - Create store structure
2. **Onboarding Phase 1** - Build onboarding flow components
3. **Onboarding Phase 2** - Connect to Figma designs, implement UI
4. **Integrations** - Build integrations page
5. **Main Scheduler** - Calendar view and components
6. **API Integration** - Connect to backend
7. **Polish** - Animations, loading states, error handling

---

## 📝 Notes

- Use Figma MCP to extract exact designs for each component
- Build reusable components for consistency
- Keep stores feature-isolated
- TypeScript for all components and stores
- Follow React best practices (hooks, composition)
- Mobile-responsive design
