import { useEffect, useState } from 'react';
import { ArrowUpRight, Bot, CircleHelp, Database, DollarSign, Headphones, RefreshCw, ShoppingBag, Users } from 'lucide-react';
import { api } from '../services/api.js';
import { BarsChart, DonutChart } from '../components/charts/Charts.jsx';
import { EmptyState, ErrorState, LoadingState, PageHeader, Panel } from '../components/common/States.jsx';
import MetricCard from '../components/common/MetricCard.jsx';
import { number } from '../utils/format.js';

export default function Overview() {
  const [data, setData] = useState(null); const [loading, setLoading] = useState(true); const [error, setError] = useState('');
  const load = async () => { setLoading(true); setError(''); const results = await Promise.allSettled([api.customerSummary(), api.ticketSummary(), api.database(), api.availability()]); if (results.every((result) => result.status === 'rejected')) setError('The backend is unavailable. Check that FastAPI is running.'); setData(results.map((result) => result.status === 'fulfilled' ? result.value : null)); setLoading(false); };
  useEffect(() => { load(); }, []);
  const [customers, tickets, db, availability] = data || [];
  const customerCount = ['complete', 'insufficient_data_for_clustering'].includes(customers?.status) ? customers.customer_count : null;
  const orderCount = db?.tables?.orders?.rows ?? db?.tables?.order?.rows ?? null;
  const atRisk = customers?.churn_risk_distribution ? Object.entries(customers.churn_risk_distribution).filter(([key]) => /high|critical|at.?risk/i.test(key)).reduce((sum, [, value]) => sum + Number(value || 0), 0) : null;
  const segmentData = (customers?.segment_counts || []).map((row) => ({ name: row.segment_name, value: row.customer_count }));
  const ticketData = Object.entries(tickets?.category_counts || {}).map(([name, value]) => ({ name, value }));
  const dataMissing = availability && (availability.dataset_count === 0 || (availability.missing || []).length > 0);
  return <>
    <PageHeader eyebrow="MONDAY, YOUR DATA AT A GLANCE" title="Overview" description="A calm, live view of customer, order and support signals." action={<button className="button button-secondary" onClick={load}><RefreshCw size={15} /> Refresh data</button>} />
    {error && <ErrorState message={error} retry={load} />}
    {dataMissing && <div className="notice-banner"><Database size={17} /><span><strong>Dataset not available — upload the required CSV files.</strong> Add authorized CSVs to <code>datasets/raw/</code> to populate analytics.</span><a href="/data-quality">Data quality <ArrowUpRight size={14} /></a></div>}
    {loading ? <LoadingState /> : <>
      <div className="metric-grid">
        <MetricCard label="Total customers" value={number(customerCount)} note={customerCount == null ? 'Waiting for customer data' : 'From processed customer records'} icon={Users} />
        <MetricCard label="Total orders" value={number(orderCount)} note={orderCount == null ? 'No order table available' : 'Database aggregate'} icon={ShoppingBag} tone="teal" />
        <MetricCard label="Total revenue" value="—" note="No revenue aggregate API is available" icon={DollarSign} tone="amber" />
        <MetricCard label="At-risk customers" value={number(atRisk)} note="Inactivity heuristic; not supervised prediction" icon={CircleHelp} tone="violet" />
        <MetricCard label="Support tickets" value={number(tickets?.ticket_rows)} note={tickets?.status === 'missing_inputs' ? 'Ticket dataset not available' : 'From ticket summary'} icon={Headphones} tone="blue" />
        <MetricCard label="Customer segments" value={number(customers?.segment_count)} note={customers?.selected_k ? `Selected K = ${customers.selected_k}` : 'No segment model available'} icon={Users} tone="green" />
      </div>
      <div className="content-grid overview-charts">
        <Panel title="Revenue trend" subtitle="Completed order revenue over time"><EmptyState title="No revenue data available">A revenue trend cannot be shown until an aggregate revenue endpoint and source data are available.</EmptyState></Panel>
        <Panel title="Customer segments" subtitle="Observed RFM cluster counts"><DonutChart data={segmentData} nameKey="name" valueKey="value" empty="Dataset not available — upload the required CSV files." /></Panel>
        <Panel title="Ticket categories" subtitle="Category counts from processed support tickets"><BarsChart data={ticketData} xKey="name" yKey="value" empty="Dataset not available — upload the required CSV files." color="#36c78a" /></Panel>
        <Panel title="Recent activity" subtitle="Latest status checks from connected APIs"><div className="activity-list"><ActivityRow icon={Database} label="Customer intelligence" detail={customers?.status || 'Not available'} ok={['complete', 'insufficient_data_for_clustering'].includes(customers?.status)} /><ActivityRow icon={Headphones} label="Support intelligence" detail={tickets?.status || 'Not available'} ok={tickets?.status === 'complete'} /><ActivityRow icon={Bot} label="Database" detail={db?.exists ? `${db.table_count} tables connected` : 'No database loaded'} ok={Boolean(db?.exists)} /></div></Panel>
      </div>
    </>}
  </>;
}

function ActivityRow({ icon: Icon, label, detail, ok }) { return <div className="activity-row"><span className="activity-icon"><Icon size={16} /></span><div><strong>{label}</strong><small>{detail}</small></div><span className={`mini-status ${ok ? 'ok' : ''}`}>{ok ? 'Ready' : 'Pending'}</span></div>; }
