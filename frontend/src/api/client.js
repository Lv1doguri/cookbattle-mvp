const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const TOKEN_KEY = 'yoriwang_token';

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}
export function setToken(token) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  constructor(status, message, code) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

// Every backend error is { detail: "<string>", code: "<machine code>" }, so `.message` is
// always safe to render directly.
export async function api(path, { method = 'GET', body, form, auth = true } = {}) {
  const headers = {};
  if (auth) {
    const token = getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }
  let payload;
  if (form) {
    payload = form; // browser sets multipart boundary itself
  } else if (body !== undefined) {
    headers['Content-Type'] = 'application/json';
    payload = JSON.stringify(body);
  }

  let res;
  try {
    res = await fetch(BASE + path, { method, headers, body: payload });
  } catch {
    throw new ApiError(0, '서버에 연결할 수 없어요', 'network_error');
  }

  let data = null;
  try {
    data = await res.json();
  } catch {
    /* empty body, e.g. some error responses */
  }

  if (!res.ok) {
    if (res.status === 401 && auth) setToken(null);
    throw new ApiError(res.status, (data && data.detail) || '문제가 생겼어요', data && data.code);
  }
  return data;
}

export function imageUrl(path) {
  return path ? BASE + path : null;
}

export async function dataUrlToBlob(dataUrl) {
  const res = await fetch(dataUrl);
  return res.blob();
}
