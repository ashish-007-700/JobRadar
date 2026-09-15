const DOT_STYLES = {
  checking: 'bg-gray-400',
  connected: 'bg-green-500',
  disconnected: 'bg-red-500',
}

function TelegramStatus({ status, detail }) {
  const label =
    status === 'checking'
      ? 'Checking Telegram...'
      : status === 'connected'
        ? 'Telegram Connected'
        : 'Telegram Disconnected'

  return (
    <div className="flex items-center gap-2 text-sm text-gray-700" title={detail || undefined}>
      <span className={`h-2 w-2 rounded-full ${DOT_STYLES[status]}`} />
      {label}
      {status === 'disconnected' && (
        <span className="text-xs text-gray-500">
          — run <code className="rounded bg-gray-100 px-1">python -m app.telegram_login</code> in
          the backend
        </span>
      )}
    </div>
  )
}

export default TelegramStatus
