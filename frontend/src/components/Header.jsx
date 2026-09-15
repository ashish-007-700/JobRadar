function Header({ onFetchNow }) {
  return (
    <header className="flex items-center justify-between border-b border-gray-200 pb-4">
      <h1 className="text-2xl font-semibold text-gray-900">JobRadar</h1>
      <button
        type="button"
        onClick={onFetchNow}
        className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white opacity-50 cursor-not-allowed"
        title="Fetching will be implemented in a later section"
      >
        Fetch Now
      </button>
    </header>
  )
}

export default Header
