function SummaryStats({ todaysJobs, channels }) {
  return (
    <dl className="grid grid-cols-2 gap-4 sm:w-80">
      <div className="rounded-md border border-gray-200 p-4">
        <dt className="text-sm text-gray-500">Today's Jobs</dt>
        <dd className="text-2xl font-semibold text-gray-900">{todaysJobs}</dd>
      </div>
      <div className="rounded-md border border-gray-200 p-4">
        <dt className="text-sm text-gray-500">Channels</dt>
        <dd className="text-2xl font-semibold text-gray-900">{channels}</dd>
      </div>
    </dl>
  )
}

export default SummaryStats
