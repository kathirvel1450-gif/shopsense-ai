import { useEffect, useState } from 'react';
import { CheckCircle2, Database, Fingerprint, KeyRound, Layers3, RefreshCw, Server, ShieldCheck, WifiOff } from 'lucide-react';
import { api, API_BASE_URL } from '../services/api.js';
import { ErrorState, LoadingState, PageHeader, Panel } from '../components/common/States.jsx';

export default function SettingsPage() {
  const [state, setState] = useState({ loading: true, error: '', backend: null, assistant: null, datasets: null });
  async function load() { setState((s) => ({ ...s, loading: true, error: '' })); const values = await Promise.allSettled([api.health(), api.assistantHealth(), api.availability()]); setState({ loading: false, error: values.every((v) => v.status === 'rejected') ? 'Backend unavailable. Start FastAPI and retry.' : '', backend: values[0].status === 'fulfilled' ? values[0].value : null, assistant: values[1].status === 'fulfilled' ? values[1].value : null, datasets: values[2].status === 'fulfilled' ? values[2].value : null }); }
  useEffect(() => { load(); }, []);
  const { backend, assistant, datasets, loading, error } = state;
  const settings = [
    { icon: Server, label: 'Backend connection', value: backend?.status === 'ok' ? 'Connected' : 'Unavailable', detail: API_BASE_URL, ok: backend?.status === 'ok' },
    { icon: Layers3, label: 'Active LLM mode', value: assistant?.llm_mode === 'deterministic_mock' ? 'Deterministic mock' : assistant?.llm_mode === 'openai_compatible' ? 'OpenAI-compatible provider' : 'Not reported', detail: assistant?.llm_mode === 'deterministic_mock' ? 'No model credential is configured; responses are labeled as mock.' : 'Provider name only; no secrets are exposed.', ok: Boolean(assistant?.llm_mode) },
    { icon: Database, label: 'Retrieval backend', value: assistant?.vector_backend || 'Unavailable', detail: assistant?.retrieval_mode || 'No retrieval status reported.', ok: Boolean(assistant?.vector_backend) },
    { icon: Fingerprint, label: 'Embedding mode', value: assistant?.embedding_provider || 'Unavailable', detail: assistant?.embedding_semantic ? 'Semantic embeddings are active.' : 'Local lexical hash vectors; not semantic embeddings.', ok: Boolean(assistant?.embedding_provider) },
    { icon: ShieldCheck, label: 'Policy index health', value: assistant?.status === 'ok' ? `${assistant.indexed_chunks} indexed chunks` : assistant?.status || 'Unavailable', detail: assistant?.synthetic_policies ? 'Checked-in policy documents are marked synthetic.' : 'Policy status not reported.', ok: assistant?.status === 'ok' },
    { icon: KeyRound, label: 'Environment configuration', value: 'Backend-managed', detail: 'Secret values and API keys are never returned to the dashboard.', ok: true },
  ];
  const sourceFiles = datasets?.available || {};
  return <>
    <PageHeader eyebrow="WORKSPACE PREFERENCES" title="Settings" description="Connection and runtime information reported by the backend. Secret values are never shown." action={<button className="button button-secondary" onClick={load}><RefreshCw size={15} /> Refresh status</button>} />
    {error && <ErrorState message={error} retry={load} />}
    {loading ? <LoadingState /> : <div className="settings-grid"><Panel title="System configuration" subtitle="Safe, non-secret runtime status">{settings.map(({ icon: Icon, label, value, detail, ok }) => <div className="setting-row" key={label}><span className={`setting-icon ${ok ? '' : 'muted'}`}><Icon size={16} /></span><div className="setting-copy"><strong>{label}</strong><small>{detail}</small></div><span className={`tag ${ok ? 'tag-green' : 'tag-muted'}`}>{value}</span></div>)}</Panel><Panel title="Dataset availability" subtitle="Expected raw files only"><div className="dataset-list">{Object.entries(sourceFiles).map(([name, exists]) => <div className="dataset-row" key={name}><span className={`file-state ${exists ? 'present' : ''}`}>{exists ? <CheckCircle2 size={14} /> : <WifiOff size={14} />}</span><div><strong>{name}</strong><small>{exists ? 'Present in raw source directory' : 'Not available'}</small></div><span className={`tag ${exists ? 'tag-green' : 'tag-muted'}`}>{exists ? 'Available' : 'Missing'}</span></div>)}</div><p className="small-muted">Add authorized CSV files to <code>datasets/raw/</code>. No upload endpoint is currently configured.</p></Panel></div>}
  </>;
}
