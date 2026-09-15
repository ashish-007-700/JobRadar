import { useEffect, useState } from 'react'
import { listFetchRuns } from '../services/api'

const STATUS_LABELS = {
  completed: 'Completed',
  completed_with_errors: 'Partial',
  failed: 'Failed',
  running: 'Running',
}

function formatDateTime(value) {
  if (!value) return '—'
  try {
    return new Date(value).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
  } catch {
    return value
  }
}

function RunRow({ run }) {
  const [expanded, setExpanded] = useState(false)
  const hasErrors = run.errors?.length > 0

  return (
    <>
      <tr className="border-t border-gray-200">
        <td className="px-3 py-2 text-sm text-gray-900">{run.requested_date}</td>
        <td className="px-3 py-2 text-sm text-gray-700">{STATUS_LABELS[run.status] || run.status}</td>
        <td className="px-3 py-2 text-sm text-gray-700">{run.messages_processed ?? '—'}</td>
        <td className="px-3 py-2 text-sm text-gray-700">{run.jobs_detected ?? '—'}</td>
        <td className="px-3 py-2 text-sm text-gray-700">{run.jobs_saved ?? '—'}</td>
        <td className="px-3 py-2 text-sm text-gray-500">{formatDateTime(run.started_at)}</td>
        <td className="px-3 py-2 text-sm text-gray-500">{formatDateTime(run.completed_at)}</td>
        <td className="px-3 py-2 text-sm">
          {hasErrors && (
            <button
              type="button"
              onClick={() => setExpanded((prev) => !prev)}
              className="text-xs font-medium text-blue-600 underline"
            >
              {expanded ? 'Hide errors' : `View errors (${run.errors.length})`}
            </button>
          )}
        </td>
      </tr>
      {expanded && hasErrors && (
        <tr className="border-t border-gray-100 bg-gray-50">
          <td colSpan={8} className="px-3 py-2">
            <ul className="list-inside list-disc text-sm text-red-700">
              {run.errors.map((err, index) => (
                <li key={index}>
                  {err.channel_username && `@${err.channel_username}: `}
                  {err.detail}
                </li>
              ))}
            </ul>
          </td>
        </tr>
      )}
    </>
  )
}

function FetchHistory() {
  const [runs, setRuns] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    listFetchRuns(20)
      .then(setRuns)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <h1 className="text-xl font-semibold text-gray-900">Fetch History</h1>
      <p className="mt-1 text-sm text-gray-500">The most recent fetch runs, newest first.</p>

      {loading && <p className="mt-4 text-sm text-gray-500">Loading...</p>}
      {error && <p className="mt-4 text-sm text-red-600">{error}</p>}

      {!loading && !error && (
        <div className="mt-4 overflow-x-auto rounded-md border border-gray-200">
          <table className="min-w-full divide-y divide-gray-200">
            <thead>
              <tr className="text-left text-xs font-medium uppercase text-gray-500">
                <th className="px-3 py-2">Date</th>
                <th className="px-3 py-2">Status</th>
                <th className="px-3 py-2">Messages</th>
                <th className="px-3 py-2">Jobs detected</th>
                <th className="px-3 py-2">Jobs saved</th>
                <th className="px-3 py-2">Started</th>
                <th className="px-3 py-2">Completed</th>
                <th className="px-3 py-2"></th>
              </tr>
            </thead>
            <tbody>
              {runs.length === 0 && (
                <tr>
                  <td colSpan={8} className="px-3 py-4 text-center text-sm text-gray-500">
                    No fetch runs yet.
                  </td>
                </tr>
              )}
              {runs.map((run) => (
                <RunRow key={run.id} run={run} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

export default FetchHistory
