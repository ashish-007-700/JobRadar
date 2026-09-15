import { useEffect, useState } from 'react'
import {
  createChannel,
  deleteChannel,
  listChannels,
  updateChannel,
  validateChannel,
} from '../services/api'

function Channels() {
  const [channels, setChannels] = useState([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState(null)

  const [newChannel, setNewChannel] = useState('')
  const [adding, setAdding] = useState(false)
  const [addError, setAddError] = useState(null)

  const [busyId, setBusyId] = useState(null)
  const [messages, setMessages] = useState({})

  const loadChannels = async () => {
    setLoading(true)
    setLoadError(null)
    try {
      setChannels(await listChannels())
    } catch (err) {
      setLoadError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadChannels()
  }, [])

  const handleAdd = async (event) => {
    event.preventDefault()
    if (!newChannel.trim()) return

    setAdding(true)
    setAddError(null)
    try {
      await createChannel(newChannel.trim())
      setNewChannel('')
      await loadChannels()
    } catch (err) {
      setAddError(err.message)
    } finally {
      setAdding(false)
    }
  }

  const handleToggle = async (channel) => {
    setBusyId(channel.id)
    try {
      await updateChannel(channel.id, { enabled: !channel.enabled })
      await loadChannels()
    } catch (err) {
      setMessages((prev) => ({ ...prev, [channel.id]: err.message }))
    } finally {
      setBusyId(null)
    }
  }

  const handleDelete = async (channel) => {
    setBusyId(channel.id)
    try {
      await deleteChannel(channel.id)
      await loadChannels()
    } catch (err) {
      setMessages((prev) => ({ ...prev, [channel.id]: err.message }))
      setBusyId(null)
    }
  }

  const handleValidate = async (channel) => {
    setBusyId(channel.id)
    try {
      const result = await validateChannel(channel.id)
      setMessages((prev) => ({
        ...prev,
        [channel.id]: result.accessible ? 'Channel is accessible.' : result.detail,
      }))
      if (result.accessible) await loadChannels()
    } catch (err) {
      setMessages((prev) => ({ ...prev, [channel.id]: err.message }))
    } finally {
      setBusyId(null)
    }
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <h1 className="text-xl font-semibold text-gray-900">Telegram Channels</h1>

      <form onSubmit={handleAdd} className="mt-4 flex gap-2">
        <input
          type="text"
          value={newChannel}
          onChange={(event) => setNewChannel(event.target.value)}
          placeholder="@channel or https://t.me/channel"
          className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm"
        />
        <button
          type="submit"
          disabled={adding}
          className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          {adding ? 'Adding...' : '+ Add Channel'}
        </button>
      </form>
      {addError && <p className="mt-2 text-sm text-red-600">{addError}</p>}

      {loading && <p className="mt-6 text-sm text-gray-500">Loading channels...</p>}
      {loadError && <p className="mt-6 text-sm text-red-600">{loadError}</p>}

      {!loading && !loadError && (
        <ul className="mt-6 divide-y divide-gray-200 rounded-md border border-gray-200">
          {channels.length === 0 && (
            <li className="p-4 text-sm text-gray-500">No channels configured yet.</li>
          )}
          {channels.map((channel) => (
            <li
              key={channel.id}
              className="flex flex-col gap-2 p-4 sm:flex-row sm:items-center sm:justify-between"
            >
              <div>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={channel.enabled}
                    disabled={busyId === channel.id}
                    onChange={() => handleToggle(channel)}
                  />
                  <span className="font-medium text-gray-900">
                    @{channel.channel_username}
                  </span>
                </label>
                <p className="text-sm text-gray-500">{channel.channel_name}</p>
                {messages[channel.id] && (
                  <p className="text-xs text-gray-500">{messages[channel.id]}</p>
                )}
              </div>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => handleValidate(channel)}
                  disabled={busyId === channel.id}
                  className="rounded-md border border-gray-300 px-3 py-1 text-xs font-medium text-gray-700 disabled:opacity-50"
                >
                  {busyId === channel.id ? 'Working...' : 'Revalidate'}
                </button>
                <button
                  type="button"
                  onClick={() => handleDelete(channel)}
                  disabled={busyId === channel.id}
                  className="rounded-md border border-red-300 px-3 py-1 text-xs font-medium text-red-600 disabled:opacity-50"
                >
                  Delete
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export default Channels
