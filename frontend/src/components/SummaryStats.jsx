const STATS = [
  { key: 'jobsFound', label: 'Jobs Found' },
  { key: 'channels', label: 'Channels' },
  { key: 'messagesProcessed', label: 'Messages Processed' },
  { key: 'jobsSaved', label: 'Jobs Saved' },
]

function SummaryStats({ stats }) {
  return (
    <dl className="grid grid-cols-2 gap-4 sm:grid-cols-4">
      {STATS.map(({ key, label }) => (
        <div key={key} className="rounded-md border border-gray-200 p-4">
          <dt className="text-sm text-gray-500">{label}</dt>
          <dd className="text-2xl font-semibold text-gray-900">{stats[key] ?? 0}</dd>
        </div>
      ))}
    </dl>
  )
}

export default SummaryStats
