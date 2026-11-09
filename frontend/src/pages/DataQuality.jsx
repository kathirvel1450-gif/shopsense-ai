import { useEffect, useState } from 'react';
import { AlertTriangle, Check, Database, FileCheck2, Play, RefreshCw } from 'lucide-react';
import { api } from '../services/api.js';
import { BarsChart } from '../components/charts/Charts.jsx';
import { EmptyState, ErrorState, LoadingState, PageHeader, Panel } from '../components/common/States.jsx';
import { number } from '../utils/format.js';

export default function DataQuality() {
  const [snapshot, setSnapshot] = useState(null); const [loading, setLoading] = useState(true); const [error, setError] = useState(''); const [cleaning, setCleaning] = useState(false); const [cleanResult, setCleanResult] = useState(null);
  const load = async () => { setLoading(true); setError(''); try { const results = await Promise.allSettled([api.availability(), api.profiling(), api.eda(), api.database()]); setSnapshot(results.map((r) => r.status === 'fulfilled' ? r.value : null)); if (results.every((r) => r.status === 'rejected')) setError('Backend unavailable. Start the FastAPI service, then retry.'); } catch (e) { setError(e.message); } finally { setLoading(false); } };
  useEffect(() => { load(); }, []);
  const [availability, profiling, eda, database] = snapshot || [];
  const profiles = profiling?.datasets || {};
  const missingData = Object.entries(profiles).flatMap(([dataset, profile]) => Object.entries(profile.column_profiles || {}).map(([column, values]) => ({ name: `${dataset}: ${column}`, value: values.missing_count || 0 }))).filter((item) => item.value > 0).slice(0, 12);
  const expected = availability?.available || {};
  async function runCleaning() {
    if (!window.confirm('Run cleaning on the available CSV files? This may replace processed tables in the local database. Raw source files will be preserved.')) return;
    setCleaning(true); setCleanResult(null);
    try { setCleanResult(stripLocalPaths(await api.clean({}))); await load(); }
    catch (e) { setCleanResult({ error: e.message }); }
    finally { setCleaning(false); }
  }
  return <>
    <PageHeader eyebrow="DATA OPERATIONS" title="Data Quality Center" description="Inspect source files, profiling signals and database readiness before processing." action={<button className="button button-secondary" onClick={load}><RefreshCw size={15} /> Refresh</button>} />
    {error && <ErrorState message={error} retry={load} />}
    {loading ? <LoadingState /> : <>
      <div className="metric-grid metric-grid-four"><Metric label="Source files found" value={availability?.dataset_count ?? '—'} icon={Database} /><Metric label="Datasets profiled" value={Object.keys(profiles).length} icon={FileCheck2} /><Metric label="EDA charts available" value={eda?.chart_count ?? '—'} icon={Play} /><Metric label="Database tables" value={database?.exists ? database.table_count : 0} icon={Database} /></div>
      <div className="content-grid data-top-grid">
        <Panel title="Dataset availability" subtitle="Expected raw source files"><div className="dataset-list">{Object.keys(expected).length ? Object.entries(expected).map(([file, present]) => <div className="dataset-row" key={file}><span className={`file-state ${present ? 'present' : ''}`}>{present ? <Check size={14} /> : <AlertTriangle size={14} />}</span><div><strong>{file}</strong><small>{present ? 'Ready to profile' : 'Missing from datasets/raw/'}</small></div><span className={`tag ${present ? 'tag-green' : 'tag-muted'}`}>{present ? 'Available' : 'Missing'}</span></div>) : <EmptyState title="Availability check unavailable">The backend did not return the dataset availability schema.</EmptyState>}</div>{availability?.dataset_count === 0 && <p className="inline-note">Dataset not available — upload the required CSV files. Place authorized CSV files in <code>datasets/raw/</code>; this project does not currently provide a browser upload endpoint.</p>}</Panel>
        <Panel title="Database status" subtitle="Local aggregate statistics only">{database?.exists ? <div className="table-wrap"><table><thead><tr><th>Table</th><th>Rows</th><th>Columns</th></tr></thead><tbody>{Object.entries(database.tables || {}).map(([name, stats]) => <tr key={name}><td>{name}</td><td>{number(stats.rows)}</td><td>{stats.columns?.length ?? '—'}</td></tr>)}</tbody></table></div> : <EmptyState title="Database not available">No imported tables were reported. Run the Phase 3 pipeline after source data is supplied.</EmptyState>}</Panel>
      </div>
      <div className="content-grid data-bottom-grid">
        <Panel title="Missing values" subtitle="Counts by column; source values are never displayed"><BarsChart data={missingData} xKey="name" yKey="value" empty="No profiled source columns or missing values are available." color="#fbbf24" /></Panel>
        <Panel title="Profiling summary" subtitle="Rows, columns and exact duplicates"><div className="table-wrap"><table><thead><tr><th>Dataset</th><th>Rows</th><th>Columns</th><th>Duplicate rows</th></tr></thead><tbody>{Object.entries(profiles).map(([name, profile]) => <tr key={name}><td>{name}</td><td>{number(profile.rows)}</td><td>{number(profile.columns_count)}</td><td>{number(profile.duplicate_rows)}</td></tr>)}</tbody></table>{!Object.keys(profiles).length && <EmptyState title="No profiling reports">Dataset not available — upload the required CSV files.</EmptyState>}</div></Panel>
      </div>
      <Panel title="Cleaning audit" subtitle="Cleaning runs use the existing configured backend pipeline" action={<button className="button button-primary" onClick={runCleaning} disabled={cleaning}><Play size={14} />{cleaning ? 'Running…' : 'Run data cleaning'}</button>}>
        <p className="safe-note"><AlertTriangle size={15} />You will be asked to confirm. The backend preserves raw CSV files, but may replace processed tables.</p>
        {cleanResult ? <pre className={`result-code ${cleanResult.error ? 'text-error' : ''}`}>{cleanResult.error || JSON.stringify(cleanResult, null, 2)}</pre> : <div className="empty-inline">{profiling?.status === 'missing_inputs' ? 'No source rows are available to clean.' : 'No cleaning action has been run in this session.'}</div>}
        {eda?.charts?.length > 0 && <div className="chart-tags">{eda.charts.map((chart) => <span className="tag tag-green" key={chart.chart}>{chart.title}</span>)}</div>}
      </Panel>
    </>}
  </>;
}

function Metric({ label, value, icon: Icon }) { return <article className="metric-card"><span className="metric-icon tone-green"><Icon size={18} /></span><div className="metric-label">{label}</div><div className="metric-value">{value}</div></article>; }

function stripLocalPaths(value) {
  if (Array.isArray(value)) return value.map(stripLocalPaths);
  if (!value || typeof value !== 'object') return value;
  return Object.fromEntries(Object.entries(value).filter(([key]) => !/(^|_)(path|directory|file_path)$/i.test(key)).map(([key, item]) => [key, stripLocalPaths(item)]));
}
