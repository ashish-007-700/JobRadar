import { useEffect, useState } from 'react'
import Header from '../components/Header'
import JobCard from '../components/JobCard'
import JobFilters from '../components/JobFilters'
import SummaryStats from '../components/SummaryStats'
import { checkTelegramHealth, fetchTelegramMessages, listChannels, listJobs } from '../services/api'

function todayIsoDate() {
  return new Date().toISOString().slice(0, 10)
}

function matchesClientFilter(job, field, value) {
  if (!value) return true
  const jobValue = job[field]
  return typeof jobValue === 'string' && jobValue.toLowerCase().includes(value.toLowerCase())
}

function Dashboard() {
  const [date, setDate] = useState(todayIsoDate())
  const [telegramStatus, setTelegramStatus] = useState('checking')
  const [telegramDetail, setTelegramDetail] = useState(null)

  const [jobs, setJobs] = useState([])
  const [jobsLoading, setJobsLoading] = useState(true)
  const [jobsError, setJobsError] = useState(null)

  const [channelCount, setChannelCount] = useState(0)

  const [filters, setFilters] = useState({
    company: '',
    location: '',
    experience: '',
    employmentType: '',
  })

  const [fetching, setFetching] = useState(false)
  const [fetchError, setFetchError] = useState(null)
  const [lastFetchResult, setLastFetchResult] = useState(null)

  useEffect(() => {
    checkTelegramHealth()
      .then((result) => {
        setTelegramStatus(result.authenticated ? 'connected' : 'disconnected')
        setTelegramDetail(result.detail || null)
      })
      .catch(() => {
        setTelegramStatus('disconnected')
        setTelegramDetail('Backend unreachable')
      })

    listChannels()
      .then((channels) => setChannelCount(channels.filter((c) => c.enabled).length))
      .catch(() => setChannelCount(0))
  }, [])

  const loadJobs = async () => {
    setJobsLoading(true)
    setJobsError(null)
    try {
      const data = await listJobs({
        date,
        company: filters.company || undefined,
        location: filters.location || undefined,
      })
      setJobs(data)
    } catch (err) {
      setJobsError(err.message)
    } finally {
      setJobsLoading(false)
    }
  }

  useEffect(() => {
    loadJobs()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [date, filters.company, filters.location])

  const handleFetchMessages = async () => {
    setFetching(true)
    setFetchError(null)
    try {
      const result = await fetchTelegramMessages(date, true, true)
      setLastFetchResult(result)
      await loadJobs()
    } catch (err) {
      setFetchError(err.message)
    } finally {
      setFetching(false)
    }
  }

  const visibleJobs = jobs.filter(
    (job) =>
      matchesClientFilter(job, 'experience', filters.experience) &&
      matchesClientFilter(job, 'employment_type', filters.employmentType)
  )

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <Header
        date={date}
        onDateChange={setDate}
        onFetch={handleFetchMessages}
        fetching={fetching}
        telegramStatus={telegramStatus}
        telegramDetail={telegramDetail}
      />

      {fetchError && (
        <p className="mt-4 rounded-md bg-red-50 p-3 text-sm text-red-700">{fetchError}</p>
      )}
      {lastFetchResult && !fetchError && (
        <p className="mt-4 rounded-md bg-green-50 p-3 text-sm text-green-800">
          Fetch complete — messages processed: {lastFetchResult.messages_found}, jobs detected:{' '}
          {lastFetchResult.jobs_detected}, jobs saved: {lastFetchResult.jobs_saved}.
        </p>
      )}

      <div className="mt-6">
        <SummaryStats
          stats={{
            jobsFound: jobs.length,
            channels: channelCount,
            messagesProcessed: lastFetchResult?.messages_found ?? 0,
            jobsSaved: lastFetchResult?.jobs_saved ?? 0,
          }}
        />
      </div>

      <div className="mt-6">
        <JobFilters filters={filters} onChange={setFilters} />
      </div>

      <div className="mt-6">
        {jobsLoading && <p className="text-sm text-gray-500">Loading jobs...</p>}
        {jobsError && <p className="text-sm text-red-600">{jobsError}</p>}

        {!jobsLoading && !jobsError && visibleJobs.length === 0 && (
          <div className="rounded-md border border-dashed border-gray-300 p-8 text-center text-gray-500">
            <p>No jobs found for this date.</p>
            <p className="mt-1 text-sm">Try fetching Telegram messages.</p>
          </div>
        )}

        {!jobsLoading && !jobsError && visibleJobs.length > 0 && (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {visibleJobs.map((job) => (
              <JobCard key={job.id} job={job} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default Dashboard
