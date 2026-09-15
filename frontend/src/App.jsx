import { useState } from 'react'
import Channels from './pages/Channels'
import Dashboard from './pages/Dashboard'
import FetchHistory from './pages/FetchHistory'
import FetchTest from './pages/FetchTest'

const TABS = [
  { id: 'dashboard', label: 'Dashboard', Component: Dashboard },
  { id: 'channels', label: 'Channels', Component: Channels },
  { id: 'history', label: 'Fetch History', Component: FetchHistory },
  { id: 'fetch-test', label: 'Debug: Fetch Test', Component: FetchTest },
]

function App() {
  const [tab, setTab] = useState('dashboard')
  const ActiveComponent = TABS.find((t) => t.id === tab).Component

  return (
    <div>
      <nav className="border-b border-gray-200">
        <div className="mx-auto flex max-w-5xl gap-4 px-4 py-3 text-sm font-medium">
          {TABS.map(({ id, label }) => (
            <button
              key={id}
              type="button"
              onClick={() => setTab(id)}
              className={tab === id ? 'text-blue-600' : 'text-gray-500'}
            >
              {label}
            </button>
          ))}
        </div>
      </nav>
      <ActiveComponent />
    </div>
  )
}

export default App
