import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Home from './pages/Home';
import Onboarding from './features/onboarding/pages/Onboarding';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/onboarding" element={<Onboarding />} />
        <Route path="/" element={<Home />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
