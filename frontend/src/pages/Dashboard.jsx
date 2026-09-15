import { useEffect, useState } from 'react'
import BackendStatus from '../components/BackendStatus'
import Header from '../components/Header'
import SummaryStats from '../components/SummaryStats'
import { checkHealth } from '../services/api'

function Dashboard() {
  const [backendStatus, setBackendStatus] = useState('checking')

  useEffect(() => {
    checkHealth()
      .then(() => setBackendStatus('connected'))
      .catch(() => setBackendStatus('unreachable'))
  }, [])

  const handleFetchNow = () => {
    // Fetching is implemented in a later section.
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <Header onFetchNow={handleFetchNow} />

      <div className="mt-4">
        <BackendStatus status={backendStatus} />
      </div>

      <div className="mt-6">
        <SummaryStats todaysJobs={0} channels={0} />
      </div>

      <div className="mt-8 rounded-md border border-dashed border-gray-300 p-8 text-center text-gray-500">
        No jobs fetched yet.
      </div>
    </div>
  )
}

export default Dashboard
