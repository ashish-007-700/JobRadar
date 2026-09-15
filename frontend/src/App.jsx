import { useEffect, useState } from 'react'

function App() {
  const [apiStatus, setApiStatus] = useState('checking...')

  useEffect(() => {
    fetch('/api/health')
      .then((res) => res.json())
      .then((data) => setApiStatus(data.status))
      .catch(() => setApiStatus('unreachable'))
  }, [])

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center space-y-2">
        <h1 className="text-3xl font-semibold text-gray-900">JobRadar</h1>
        <p className="text-gray-500">Backend status: {apiStatus}</p>
      </div>
    </div>
  )
}

export default App
