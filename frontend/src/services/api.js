const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');

export class ApiError extends Error {
  constructor(message, status = 0, payload = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.payload = payload;
  }
}

export async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers: { Accept: 'application/json', ...(options.body ? { 'Content-Type': 'application/json' } : {}), ...options.headers },
    });
  } catch (error) {
    throw new ApiError(error instanceof Error ? error.message : 'Backend unavailable');
  }
  let payload;
  try { payload = await response.json(); } catch { payload = null; }
  if (!response.ok) {
    const detail = payload?.detail;
    const message = typeof detail === 'string' ? detail : `Request failed (${response.status})`;
    throw new ApiError(message, response.status, payload);
  }
  return payload;
}

const get = (path) => request(path);
const post = (path, body) => request(path, { method: 'POST', body: JSON.stringify(body) });

export const api = {
  health: () => get('/api/health'),
  availability: () => get('/api/datasets/availability'),
  profiling: () => get('/api/data/profiling'),
  eda: () => get('/api/data/eda'),
  clean: (strategy = {}) => post('/api/data/cleaning', strategy),
  database: () => get('/api/database/statistics'),
  customerRfm: () => get('/api/customers/rfm'),
  customerSegments: () => get('/api/customers/segments'),
  customerRisk: () => get('/api/customers/churn-risk'),
  customerEvaluation: () => get('/api/customers/model-evaluation'),
  customerSummary: () => get('/api/customers/summary'),
  ticketSummary: () => get('/api/tickets/summary'),
  validateTicket: (ticket_text) => post('/api/tickets/validate', { ticket_text }),
  classifyTicket: (ticket_text, method = 'zero_shot') => post('/api/tickets/classify', { ticket_text, method }),
  processTickets: (ticket_text, method = 'zero_shot') => post('/api/tickets/process', { ticket_text, method }),
  assistantHealth: () => get('/api/assistant/health'),
  retrieve: (question) => post('/api/assistant/retrieve', { question }),
  chat: (question, conversation_id) => post('/api/assistant/chat', { question, conversation_id }),
  refund: (question, conversation_id) => post('/api/assistant/refund', { question, conversation_id }),
  escalate: (summary, conversation_id) => post('/api/assistant/escalate', { summary, conversation_id }),
};

export async function checkApiHealth() {
  try { return { ok: (await api.health())?.status === 'ok' }; }
  catch (error) { return { ok: false, detail: error.message }; }
}

export { API_BASE_URL };
