const STATE_STYLES = {
  running: 'bg-blue-50 text-blue-800',
  completed: 'bg-green-50 text-green-800',
  partial: 'bg-yellow-50 text-yellow-800',
  failed: 'bg-red-50 text-red-700',
}

const STATE_LABELS = {
  running: 'Fetching Telegram messages...',
  completed: 'Completed',
  partial: 'Completed with errors',
  failed: 'Failed',
}

function FetchStatusPanel({ state, lastRun, fetchError, onRetry }) {
  if (state === 'idle' && !lastRun) return null

  return (
    <div className={`mt-4 rounded-md p-3 text-sm ${STATE_STYLES[state] || 'bg-gray-50 text-gray-700'}`}>
      <p className="font-medium">{STATE_LABELS[state] || state}</p>

      {state !== 'running' && lastRun && (
        <p className="mt-1">
          {lastRun.messages_processed ?? 0} messages · {lastRun.jobs_detected ?? 0} jobs detected ·{' '}
          {lastRun.jobs_saved ?? 0} saved
          {lastRun.jobs_duplicate > 0 && ` · ${lastRun.jobs_duplicate} already saved (skipped)`}
        </p>
      )}

      {fetchError && <p className="mt-1">{fetchError}</p>}

      {lastRun?.errors?.length > 0 && (
        <ul className="mt-2 list-inside list-disc space-y-0.5">
          {lastRun.errors.slice(0, 5).map((err, index) => (
            <li key={index}>
              {err.channel_username && `@${err.channel_username}: `}
              {err.detail}
            </li>
          ))}
        </ul>
      )}

      {(state === 'failed' || state === 'partial') && onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-2 rounded-md border border-current px-3 py-1 text-xs font-medium"
        >
          Retry
        </button>
      )}
    </div>
  )
}

export default FetchStatusPanel
