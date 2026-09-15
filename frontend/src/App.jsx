import { useState } from 'react'
import Channels from './pages/Channels'
import Dashboard from './pages/Dashboard'

const TABS = [
  { id: 'dashboard', label: 'Dashboard' },
  { id: 'channels', label: 'Channels' },
]

function App() {
  const [tab, setTab] = useState('dashboard')

  return (
    <div>
      <nav className="border-b border-gray-200">
        <div className="mx-auto flex max-w-3xl gap-4 px-4 py-3 text-sm font-medium">
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
      {tab === 'dashboard' ? <Dashboard /> : <Channels />}
    </div>
  )
}

export default App
