import { ArrowDownRight, ArrowUpRight, Minus } from 'lucide-react';

export default function MetricCard({ label, value, note, icon: Icon, tone = 'green', change }) {
  const Trend = change > 0 ? ArrowUpRight : change < 0 ? ArrowDownRight : Minus;
  return <article className="metric-card"><div className={`metric-icon tone-${tone}`}>{Icon && <Icon size={18} />}</div><div className="metric-label">{label}</div><div className="metric-value">{value ?? '—'}</div><div className="metric-foot">{change != null ? <span className="metric-change"><Trend size={13} />{Math.abs(change)}%</span> : null}{note}</div></article>;
}
