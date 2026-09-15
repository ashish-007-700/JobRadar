function JobFilters({ filters, onChange }) {
  const update = (field) => (event) => onChange({ ...filters, [field]: event.target.value })

  return (
    <div className="flex flex-wrap gap-2">
      <input
        type="text"
        placeholder="Company"
        value={filters.company}
        onChange={update('company')}
        className="rounded-md border border-gray-300 px-3 py-2 text-sm"
      />
      <input
        type="text"
        placeholder="Location"
        value={filters.location}
        onChange={update('location')}
        className="rounded-md border border-gray-300 px-3 py-2 text-sm"
      />
      <input
        type="text"
        placeholder="Experience"
        value={filters.experience}
        onChange={update('experience')}
        className="rounded-md border border-gray-300 px-3 py-2 text-sm"
      />
      <input
        type="text"
        placeholder="Employment type"
        value={filters.employmentType}
        onChange={update('employmentType')}
        className="rounded-md border border-gray-300 px-3 py-2 text-sm"
      />
    </div>
  )
}

export default JobFilters
