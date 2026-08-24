import { Link, Outlet } from 'react-router-dom'

export default function App() {
  return (
    <div className="min-h-screen bg-bg">
      <header className="sticky top-0 z-30 border-b border-border/60 bg-bg-deep/90 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3 sm:px-6">
          <Link to="/" className="cursor-pointer font-display text-2xl font-bold tracking-wide text-text">
            UFC<span className="text-brand">PREDICT</span>
          </Link>
          <nav className="flex items-center gap-4">
            <Link
              to="/chat"
              className="cursor-pointer rounded-full border border-border px-4 py-1.5 text-sm font-medium text-text-muted transition-colors duration-200 hover:border-brand hover:text-text"
            >
              Ask the AI
            </Link>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6 sm:px-6">
        <Outlet />
      </main>
    </div>
  )
}
