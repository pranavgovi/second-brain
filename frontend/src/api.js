const BASE_URL = 'http://127.0.0.1:8000'

async function handleResponse(res) {
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `Request failed with status ${res.status}`)
  }
  return res.json()
}

export function ingestText({ title, content, tags }) {
  return fetch(`${BASE_URL}/ingest/text`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, content, tags: tags || null }),
  }).then(handleResponse)
}

export function ingestUrl({ url, title, tags }) {
  return fetch(`${BASE_URL}/ingest/url`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url, title: title || null, tags: tags || null }),
  }).then(handleResponse)
}

export function ingestFile({ file, title, tags }) {
  const formData = new FormData()
  formData.append('file', file)
  if (title) formData.append('title', title)
  if (tags) formData.append('tags', tags)

  return fetch(`${BASE_URL}/ingest/file`, {
    method: 'POST',
    body: formData,
  }).then(handleResponse)
}

export function listIngested() {
  return fetch(`${BASE_URL}/ingest`).then(handleResponse)
}

export function ask(question) {
  return fetch(`${BASE_URL}/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  }).then(handleResponse)
}
