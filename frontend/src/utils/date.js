// Returns today's date as YYYY-MM-DD using the browser's LOCAL calendar day,
// not UTC. `Date#toISOString()` converts to UTC first, which silently shifts
// the date near midnight depending on the user's timezone offset (e.g. it can
// show tomorrow's date while it's still today locally) — the same off-by-one
// mistake the backend's APP_TIMEZONE handling exists to avoid.
export function todayIsoDate() {
  const now = new Date()
  const year = now.getFullYear()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}
