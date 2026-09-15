const STATUS_STYLES = {
  checking: 'bg-gray-100 text-gray-600',
  connected: 'bg-green-100 text-green-700',
  unreachable: 'bg-red-100 text-red-700',
}

const STATUS_LABELS = {
  checking: 'Checking backend...',
  connected: 'Backend connected',
  unreachable: 'Backend unreachable',
}

function BackendStatus({ status }) {
  return (
    <span
      className={`inline-block rounded-full px-3 py-1 text-xs font-medium ${STATUS_STYLES[status]}`}
    >
      {STATUS_LABELS[status]}
    </span>
  )
}

export default BackendStatus
