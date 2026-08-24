import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import './index.css'
import App from './App.tsx'
import EventsPage from './pages/EventsPage.tsx'
import EventDetailPage from './pages/EventDetailPage.tsx'
import FightDetailPage from './pages/FightDetailPage.tsx'
import ChatPage from './pages/ChatPage.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<App />}>
          <Route index element={<EventsPage />} />
          <Route path="events/:slug" element={<EventDetailPage />} />
          <Route path="fights/:id" element={<FightDetailPage />} />
          <Route path="chat" element={<ChatPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  </StrictMode>,
)
