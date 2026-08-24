import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import { api } from '../api/client'
import type { Citation } from '../api/types'
import CitationList from '../components/CitationList'

interface Message {
  role: 'user' | 'assistant'
  text: string
  citations?: Citation[]
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  async function send() {
    const text = input.trim()
    if (!text || loading) return
    setInput('')
    setError(null)
    setMessages((m) => [...m, { role: 'user', text }])
    setLoading(true)
    try {
      const res = await api.chat(text)
      setMessages((m) => [...m, { role: 'assistant', text: res.response, citations: res.citations }])
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex h-[calc(100vh-6.5rem)] flex-col">
      <h1 className="mb-4 font-display text-3xl font-bold tracking-wide text-text">Ask the AI</h1>

      <div className="flex-1 space-y-4 overflow-y-auto rounded-xl border border-border bg-surface p-4 sm:p-6">
        {messages.length === 0 && (
          <p className="text-sm text-text-muted">
            Ask about anything fans or analysts are saying — e.g. "who's been talking trash lately?" or "what's the
            latest on Islam Makhachev?"
          </p>
        )}
        {messages.map((m, i) => (
          <div key={i} className={m.role === 'user' ? 'ml-auto max-w-[85%]' : 'max-w-[90%]'}>
            <div
              className={
                m.role === 'user'
                  ? 'rounded-xl rounded-tr-sm bg-brand px-4 py-2 text-white'
                  : 'rounded-xl rounded-tl-sm border border-border bg-bg px-4 py-3'
              }
            >
              {m.role === 'assistant' ? (
                <div className="prose prose-invert prose-sm max-w-none [&_p]:my-1 [&_p]:text-text/90">
                  <ReactMarkdown>{m.text}</ReactMarkdown>
                </div>
              ) : (
                <p>{m.text}</p>
              )}
            </div>
            {m.citations && m.citations.length > 0 && (
              <details className="mt-2">
                <summary className="cursor-pointer text-xs text-text-muted hover:text-text">
                  {m.citations.length} source{m.citations.length > 1 ? 's' : ''}
                </summary>
                <div className="mt-2">
                  <CitationList citations={m.citations} />
                </div>
              </details>
            )}
          </div>
        ))}
        {loading && (
          <div className="max-w-[90%] rounded-xl rounded-tl-sm border border-border bg-bg px-4 py-3">
            <div className="flex gap-1">
              <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-text-muted [animation-delay:-0.3s]" />
              <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-text-muted [animation-delay:-0.15s]" />
              <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-text-muted" />
            </div>
          </div>
        )}
        {error && <p className="text-sm text-brand-hover">Error: {error}</p>}
        <div ref={bottomRef} />
      </div>

      <div className="mt-4 flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && send()}
          placeholder="Ask a question…"
          className="flex-1 rounded-full border border-border bg-surface px-4 py-2.5 text-text placeholder:text-text-muted focus:border-brand focus:outline-none"
        />
        <button
          onClick={send}
          disabled={loading || !input.trim()}
          className="cursor-pointer rounded-full bg-brand px-5 py-2.5 text-sm font-semibold text-white transition-colors duration-200 hover:bg-brand-hover disabled:cursor-not-allowed disabled:opacity-60"
        >
          Send
        </button>
      </div>
    </div>
  )
}
