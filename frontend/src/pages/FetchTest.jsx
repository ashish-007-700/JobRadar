import { useState } from 'react'
import { fetchTelegramMessages } from '../services/api'

function todayIsoDate() {
  return new Date().toISOString().slice(0, 10)
}

function FetchTest() {
  const [date, setDate] = useState(todayIsoDate())
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null)
  const [expandedId, setExpandedId] = useState(null)

  const handleFetch = async () => {
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      setResult(await fetchTelegramMessages(date))
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <h1 className="text-xl font-semibold text-gray-900">Fetch Test</h1>
      <p className="mt-1 text-sm text-gray-500">
        Retrieve raw Telegram messages for a date. This does not detect jobs or save
        anything yet — it's for verifying the fetch pipeline.
      </p>

      <div className="mt-4 flex gap-2">
        <input
          type="date"
          value={date}
          onChange={(event) => setDate(event.target.value)}
          className="rounded-md border border-gray-300 px-3 py-2 text-sm"
        />
        <button
          type="button"
          onClick={handleFetch}
          disabled={loading}
          className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          {loading ? 'Fetching...' : 'Fetch Messages'}
        </button>
      </div>

      {error && <p className="mt-4 text-sm text-red-600">{error}</p>}

      {result && (
        <div className="mt-6">
          <p className="text-sm text-gray-700">Date: {result.date}</p>
          <p className="text-sm text-gray-700">
            Channels processed: {result.channels_processed}
          </p>
          <p className="text-sm text-gray-700">Messages found: {result.messages_found}</p>

          <ul className="mt-3 space-y-1 text-sm">
            {result.channel_results.map((cr) => (
              <li key={cr.channel_username} className={cr.status === 'error' ? 'text-red-600' : 'text-gray-700'}>
                @{cr.channel_username} — {cr.status === 'error' ? cr.detail : cr.message_count}
              </li>
            ))}
          </ul>

          <div className="mt-6 divide-y divide-gray-200 rounded-md border border-gray-200">
            {result.messages.length === 0 && (
              <p className="p-4 text-sm text-gray-500">No messages for this date.</p>
            )}
            {result.messages.map((message) => {
              const key = `${message.channel_username}-${message.message_id}`
              const expanded = expandedId === key
              return (
                <div key={key} className="p-3">
                  <button
                    type="button"
                    onClick={() => setExpandedId(expanded ? null : key)}
                    className="w-full text-left text-sm"
                  >
                    <span className="font-medium text-gray-900">
                      @{message.channel_username}
                    </span>{' '}
                    <span className="text-gray-500">
                      #{message.message_id} — {message.message_date}
                    </span>
                  </button>
                  {expanded && (
                    <pre className="mt-2 whitespace-pre-wrap break-words rounded-md bg-gray-50 p-3 text-xs text-gray-700">
{JSON.stringify(message, null, 2)}
                    </pre>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

export default FetchTest
