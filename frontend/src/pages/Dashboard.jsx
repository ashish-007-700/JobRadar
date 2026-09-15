import { useEffect, useState } from 'react'
import FetchStatusPanel from '../components/FetchStatusPanel'
import Header from '../components/Header'
import JobCard from '../components/JobCard'
import JobFilters from '../components/JobFilters'
import SummaryStats from '../components/SummaryStats'
import {
  checkTelegramHealth,
  deleteJobsForDate,
  fetchTelegramMessages,
  getFetchStatus,
  listChannels,
  listJobs,
} from '../services/api'
import { todayIsoDate } from '../utils/date'

function matchesClientFilter(job, field, value) {
  if (!value) return true
  const jobValue = job[field]
  return typeof jobValue === 'string' && jobValue.toLowerCase().includes(value.toLowerCase())
}

function normalizeRun(result) {
  return {
    requested_date: result.date ?? result.requested_date,
    status: result.status,
    channels_processed: result.channels_processed,
    messages_processed: result.messages_found ?? result.messages_processed,
    jobs_detected: result.jobs_detected,
    jobs_saved: result.jobs_saved,
    jobs_duplicate: result.jobs_duplicate,
    errors: result.errors,
  }
}

function toDisplayState(runStatus) {
  if (runStatus === 'completed') return 'completed'
  if (runStatus === 'completed_with_errors') return 'partial'
  if (runStatus === 'failed') return 'failed'
  return 'idle'
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
  // Company/location hit the API server-side; debounce so typing doesn't fire
  // a request per keystroke. Experience/employment-type filter client-side
  // (see visibleJobs below) and don't need debouncing.
  const [serverFilters, setServerFilters] = useState({ company: '', location: '' })
  useEffect(() => {
    const timeout = setTimeout(() => {
      setServerFilters({ company: filters.company, location: filters.location })
    }, 400)
    return () => clearTimeout(timeout)
  }, [filters.company, filters.location])

  const [fetchState, setFetchState] = useState('idle')
  const [fetchError, setFetchError] = useState(null)
  const [lastRun, setLastRun] = useState(null)

  const [resetting, setResetting] = useState(false)
  const [resetError, setResetError] = useState(null)

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

    getFetchStatus()
      .then((status) => {
        setFetchState(status.state === 'running' ? 'running' : toDisplayState(status.last_run?.status))
        if (status.last_run) setLastRun(status.last_run)
      })
      .catch(() => {})
  }, [])

  const loadJobs = async () => {
    setJobsLoading(true)
    setJobsError(null)
    try {
      const data = await listJobs({
        date,
        company: serverFilters.company || undefined,
        location: serverFilters.location || undefined,
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
  }, [date, serverFilters.company, serverFilters.location])

  // If a fetch is already running (e.g. detected on page load), poll until it
  // finishes rather than pretending to show real-time progress.
  useEffect(() => {
    if (fetchState !== 'running') return undefined

    const interval = setInterval(async () => {
      try {
        const status = await getFetchStatus()
        if (status.state !== 'running') {
          clearInterval(interval)
          setFetchState(toDisplayState(status.last_run?.status))
          if (status.last_run) setLastRun(status.last_run)
          loadJobs()
        }
      } catch {
        // Backend temporarily unreachable; keep polling.
      }
    }, 3000)

    return () => clearInterval(interval)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fetchState])

  const handleFetchMessages = async () => {
    setFetchState('running')
    setFetchError(null)
    try {
      const result = await fetchTelegramMessages(date, true, true)
      setLastRun(normalizeRun(result))
      setFetchState(toDisplayState(result.status))
      await loadJobs()
    } catch (err) {
      setFetchError(err.message)
      setFetchState('failed')
    }
  }

  const handleResetJobs = async () => {
    const count = jobs.length
    const confirmed = window.confirm(
      count > 0
        ? `Delete all ${count} job${count === 1 ? '' : 's'} saved for ${date}? This cannot be undone.`
        : `There are no saved jobs for ${date} to delete.`
    )
    if (!confirmed || count === 0) return

    setResetting(true)
    setResetError(null)
    try {
      await deleteJobsForDate(date)
      await loadJobs()
    } catch (err) {
      setResetError(err.message)
    } finally {
      setResetting(false)
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
        fetching={fetchState === 'running'}
        telegramStatus={telegramStatus}
        telegramDetail={telegramDetail}
      />

      <FetchStatusPanel
        state={fetchState}
        lastRun={lastRun}
        fetchError={fetchError}
        onRetry={handleFetchMessages}
      />

      <div className="mt-6">
        <SummaryStats
          stats={{
            jobsFound: jobs.length,
            channels: channelCount,
            messagesProcessed: lastRun?.messages_processed ?? 0,
            jobsSaved: lastRun?.jobs_saved ?? 0,
          }}
        />
      </div>

      <div className="mt-6 flex flex-wrap items-center justify-between gap-2">
        <JobFilters filters={filters} onChange={setFilters} />
        <button
          type="button"
          onClick={handleResetJobs}
          disabled={resetting || jobsLoading}
          className="rounded-md border border-red-300 px-3 py-2 text-sm font-medium text-red-600 disabled:opacity-50"
        >
          {resetting ? 'Resetting...' : `Reset jobs for ${date}`}
        </button>
      </div>

      <div className="mt-6">
        {resetError && <p className="text-sm text-red-600">{resetError}</p>}
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
