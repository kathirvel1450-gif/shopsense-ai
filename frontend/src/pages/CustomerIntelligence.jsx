import { useEffect, useState } from 'react';
import { Activity, Crosshair, RotateCcw, Target, Users } from 'lucide-react';
import { api } from '../services/api.js';
import { BarsChart, DonutChart } from '../components/charts/Charts.jsx';
import { EmptyState, ErrorState, LoadingState, PageHeader, Panel } from '../components/common/States.jsx';
import MetricCard from '../components/common/MetricCard.jsx';
import { number } from '../utils/format.js';

export default function CustomerIntelligence() {
  const [data, setData] = useState(null); const [loading, setLoading] = useState(true); const [error, setError] = useState('');
  const load = async () => { setLoading(true); setError(''); const results = await Promise.allSettled([api.customerRfm(), api.customerSegments(), api.customerRisk(), api.customerEvaluation(), api.customerSummary()]); setData(results.map((r) => r.status === 'fulfilled' ? r.value : null)); if (results.every((r) => r.status === 'rejected')) setError('Customer intelligence API is unavailable.'); setLoading(false); };
  useEffect(() => { load(); }, []);
  const [rfm, segments, risk, evaluation, summary] = data || [];
  const ready = summary?.status === 'complete' || summary?.status === 'insufficient_data_for_clustering';
  const segmentRows = segments?.segments || [];
  const segmentDistribution = segmentRows.map((row) => ({ name: row.segment_name, value: row.customer_count }));
  const riskDistribution = Object.entries(risk?.churn_risk?.distribution || summary?.churn_risk_distribution || {}).map(([name, value]) => ({ name, value }));
  const evaluationRows = (evaluation?.evaluations || []).filter((row) => row.status === 'evaluated');
  return <>
    <PageHeader eyebrow="CUSTOMER BEHAVIOR" title="Customer Intelligence" description="RFM patterns, observed segments and transparent inactivity risk." action={<button className="button button-secondary" onClick={load}><RotateCcw size={15} /> Refresh analysis</button>} />
    <div className="notice-banner notice-info"><Activity size={17} /><span>Churn risk is an <strong>inactivity-based heuristic</strong>, not a supervised churn prediction. Segment descriptions reflect observed RFM clusters.</span></div>
    {error && <ErrorState message={error} retry={load} />}
    {loading ? <LoadingState /> : <>
      {!ready && <EmptyState title="Customer data is not ready">Dataset not available — upload the required CSV files.</EmptyState>}
      <div className="metric-grid metric-grid-four">
        <MetricCard label="Customers analyzed" value={ready ? number(summary?.customer_count) : '—'} note={ready ? 'Aggregate only; IDs are not returned' : 'Awaiting cleaned data'} icon={Users} />
        <MetricCard label="Completed order customers" value={ready ? number(rfm?.rfm_summary?.recency?.count) : '—'} note={rfm?.reference_date ? `Reference ${rfm.reference_date}` : 'No reference date reported'} icon={Target} tone="teal" />
        <MetricCard label="Selected segments" value={ready ? number(summary?.segment_count) : '—'} note={summary?.selected_k ? `Selected K = ${summary.selected_k}` : 'No feasible K selected'} icon={Crosshair} tone="blue" />
        <MetricCard label="At-risk heuristic count" value={ready && riskDistribution.length ? number(riskDistribution.filter((item) => /high|critical|at.?risk/i.test(item.name)).reduce((sum, item) => sum + Number(item.value || 0), 0)) : '—'} note="Based on configured inactivity rules" icon={Activity} tone="amber" />
      </div>
      {ready && <div className="content-grid customer-charts">
        <Panel title="RFM summary" subtitle="Aggregate values from available processed customers"><div className="rfm-grid">{['recency', 'frequency', 'monetary'].map((key) => <div className="rfm-tile" key={key}><span>{key}</span><strong>{number(rfm?.rfm_summary?.[key]?.median) ?? '—'}</strong><small>Median</small></div>)}</div><p className="small-muted">RFM summary values are aggregates; no customer-level rows are exposed through these endpoints.</p></Panel>
        <Panel title="Segment distribution" subtitle="Counts by observed RFM cluster"><DonutChart data={segmentDistribution} nameKey="name" valueKey="value" empty="Dataset not available — upload the required CSV files." /></Panel>
        <Panel title="K-Means inertia vs K" subtitle="Lower inertia is expected as K increases"><BarsChart data={evaluationRows.filter((row) => row.inertia != null).map((row) => ({ name: `K=${row.k}`, value: row.inertia }))} empty="No feasible K-Means evaluations are available." color="#2dd4bf" /></Panel>
        <Panel title="Silhouette score vs K" subtitle="Higher scores indicate tighter separated clusters"><BarsChart data={evaluationRows.filter((row) => row.silhouette_score != null).map((row) => ({ name: `K=${row.k}`, value: row.silhouette_score }))} empty="No valid silhouette scores are available." color="#60a5fa" /></Panel>
        <Panel title="Inactivity risk distribution" subtitle="Transparent heuristic classification"><DonutChart data={riskDistribution} nameKey="name" valueKey="value" empty="No risk distribution available." /></Panel>
        <Panel title="Observed segment profiles" subtitle="Cluster medians and dataset-specific descriptions"><div className="table-wrap"><table><thead><tr><th>Segment</th><th>Customers</th><th>Median recency</th><th>Median frequency</th><th>Median spend</th></tr></thead><tbody>{segmentRows.map((row) => <tr key={row.cluster_id}><td><strong>{row.segment_name}</strong><small className="table-subtext">{row.description}</small></td><td>{number(row.customer_count)}</td><td>{number(row.recency_median)} d</td><td>{number(row.frequency_median)}</td><td>{number(row.monetary_median)}</td></tr>)}</tbody></table>{segmentRows.length === 0 && <EmptyState title="No segment profiles">Clustering was not feasible for the available data.</EmptyState>}</div></Panel>
        <Panel title="K selection note" subtitle="Interpretability-aware selection"><p className="selection-note">{evaluation?.selection?.reason || 'No K selection reason was reported.'}</p><div className="small-muted">Selected K: {evaluation?.selected_k ?? '—'}. Review cluster behavior with the business owner before acting.</div></Panel>
      </div>}
    </>}
  </>;
}
