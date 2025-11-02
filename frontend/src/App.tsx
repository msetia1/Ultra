import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Home from './pages/Home';
import Onboarding from './features/onboarding/pages/Onboarding';
import CalendarPage from './features/calendar/pages/CalendarPage';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/onboarding" element={<Onboarding />} />
        <Route path="/calendar" element={<CalendarPage />} />
        <Route path="/" element={<Home />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
