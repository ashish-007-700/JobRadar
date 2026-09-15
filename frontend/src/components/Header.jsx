import TelegramStatus from './TelegramStatus'

function Header({ date, onDateChange, onFetch, fetching, telegramStatus, telegramDetail }) {
  return (
    <header className="flex flex-col gap-4 border-b border-gray-200 pb-4 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <h1 className="text-2xl font-semibold text-gray-900">JobRadar</h1>
        <div className="mt-1">
          <TelegramStatus status={telegramStatus} detail={telegramDetail} />
        </div>
      </div>

      <div className="flex items-center gap-2">
        <input
          type="date"
          value={date}
          onChange={(event) => onDateChange(event.target.value)}
          className="rounded-md border border-gray-300 px-3 py-2 text-sm"
        />
        <button
          type="button"
          onClick={onFetch}
          disabled={fetching}
          className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {fetching ? 'Fetching...' : 'Fetch Messages'}
        </button>
      </div>
    </header>
  )
}

export default Header
