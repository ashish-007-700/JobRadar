import { useEffect, useState } from 'react'
import { listJobs } from '../services/api'

function Field({ label, value }) {
  if (!value) return null
  return (
    <p className="text-sm text-gray-700">
      <span className="text-gray-500">{label}:</span> {Array.isArray(value) ? value.join(', ') : value}
    </p>
  )
}

function JobRow({ job }) {
  return (
    <li className="p-4">
      <p className="font-medium text-gray-900">
        {job.title || 'Untitled role'} {job.company ? `— ${job.company}` : ''}
      </p>
      <Field label="Location" value={job.location} />
      <Field label="Experience" value={job.experience} />
      <Field label="Qualification" value={job.qualification} />
      <Field label="Batch" value={job.batch} />
      <Field label="Salary" value={job.salary} />
      <Field label="Skills" value={job.skills} />
      <Field label="Employment type" value={job.employment_type} />
      <Field label="Posted" value={job.posted_at} />
      <div className="mt-1 flex gap-3">
        {job.original_apply_url && (
          <a
            href={job.original_apply_url}
            target="_blank"
            rel="noreferrer"
            className="text-sm text-blue-600 underline"
          >
            Original Apply URL
          </a>
        )}
        {job.final_apply_url && (
          <a
            href={job.final_apply_url}
            target="_blank"
            rel="noreferrer"
            className="text-sm text-green-700 underline"
          >
            Final Apply URL
          </a>
        )}
      </div>
    </li>
  )
}

function Jobs() {
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [filters, setFilters] = useState({ date: '', company: '', location: '' })

  const load = async (activeFilters) => {
    setLoading(true)
    setError(null)
    try {
      setJobs(await listJobs(activeFilters))
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load({})
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleFilter = (event) => {
    event.preventDefault()
    load(filters)
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <h1 className="text-xl font-semibold text-gray-900">Jobs</h1>

      <form onSubmit={handleFilter} className="mt-4 flex flex-wrap gap-2">
        <input
          type="date"
          value={filters.date}
          onChange={(e) => setFilters((prev) => ({ ...prev, date: e.target.value }))}
          className="rounded-md border border-gray-300 px-3 py-2 text-sm"
        />
        <input
          type="text"
          placeholder="Company"
          value={filters.company}
          onChange={(e) => setFilters((prev) => ({ ...prev, company: e.target.value }))}
          className="rounded-md border border-gray-300 px-3 py-2 text-sm"
        />
        <input
          type="text"
          placeholder="Location"
          value={filters.location}
          onChange={(e) => setFilters((prev) => ({ ...prev, location: e.target.value }))}
          className="rounded-md border border-gray-300 px-3 py-2 text-sm"
        />
        <button
          type="submit"
          disabled={loading}
          className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          {loading ? 'Loading...' : 'Filter'}
        </button>
      </form>

      {error && <p className="mt-4 text-sm text-red-600">{error}</p>}

      <ul className="mt-6 divide-y divide-gray-200 rounded-md border border-gray-200">
        {!loading && jobs.length === 0 && (
          <li className="p-4 text-sm text-gray-500">No jobs found.</li>
        )}
        {jobs.map((job) => (
          <JobRow key={job.id} job={job} />
        ))}
      </ul>
    </div>
  )
}

export default Jobs
