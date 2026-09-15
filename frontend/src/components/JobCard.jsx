import { useState } from 'react'

function formatPostedDate(value) {
  if (!value) return null
  try {
    return new Date(value).toLocaleString(undefined, {
      dateStyle: 'medium',
      timeStyle: 'short',
    })
  } catch {
    return value
  }
}

function DetailRow({ label, value }) {
  if (!value) return null
  return (
    <p className="text-sm text-gray-700">
      <span className="text-gray-500">{label}:</span> {Array.isArray(value) ? value.join(', ') : value}
    </p>
  )
}

function JobCard({ job }) {
  const [expanded, setExpanded] = useState(false)
  const applyUrl = job.final_apply_url || job.original_apply_url

  return (
    <div className="rounded-lg border border-gray-200 p-4 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          {job.company && <p className="text-sm font-medium text-gray-500">{job.company}</p>}
          <h3 className="text-base font-semibold text-gray-900">{job.title || 'Untitled role'}</h3>
          <p className="mt-1 text-sm text-gray-600">
            {[job.location, job.experience, job.batch].filter(Boolean).join(' · ')}
          </p>
          {job.qualification && (
            <p className="mt-1 line-clamp-2 text-sm text-gray-600">{job.qualification}</p>
          )}
          {job.salary && <p className="mt-1 text-sm font-medium text-gray-800">{job.salary}</p>}
          {job.skills?.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1">
              {job.skills.slice(0, 6).map((skill) => (
                <span
                  key={skill}
                  className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600"
                >
                  {skill}
                </span>
              ))}
            </div>
          )}
        </div>

        {applyUrl && (
          <a
            href={applyUrl}
            target="_blank"
            rel="noreferrer"
            className="shrink-0 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            Apply Now
          </a>
        )}
      </div>

      <button
        type="button"
        onClick={() => setExpanded((prev) => !prev)}
        className="mt-3 text-xs font-medium text-gray-500 underline"
      >
        {expanded ? 'Hide details' : 'View details'}
      </button>

      {expanded && (
        <div className="mt-3 space-y-1 border-t border-gray-100 pt-3">
          <DetailRow label="Employment type" value={job.employment_type} />
          <DetailRow label="Skills" value={job.skills} />
          <DetailRow label="Posted" value={formatPostedDate(job.posted_at)} />
          <DetailRow label="Telegram channel" value={job.telegram_channel ? `@${job.telegram_channel}` : null} />
          {job.telegram_message_url && (
            <p className="text-sm">
              <a
                href={job.telegram_message_url}
                target="_blank"
                rel="noreferrer"
                className="text-blue-600 underline"
              >
                View original Telegram message
              </a>
            </p>
          )}
          {job.original_apply_url && (
            <p className="text-sm">
              <a
                href={job.original_apply_url}
                target="_blank"
                rel="noreferrer"
                className="text-gray-600 underline"
              >
                Original Apply URL
              </a>
            </p>
          )}
          {job.final_apply_url && job.final_apply_url !== job.original_apply_url && (
            <p className="text-sm">
              <a
                href={job.final_apply_url}
                target="_blank"
                rel="noreferrer"
                className="text-green-700 underline"
              >
                Final Apply URL
              </a>
            </p>
          )}
        </div>
      )}
    </div>
  )
}

export default JobCard
