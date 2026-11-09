import { AlertCircle, Database, LoaderCircle } from 'lucide-react';

export function LoadingState({ label = 'Loading live data…' }) {
  return <div className="state-box" role="status"><LoaderCircle className="spin" size={18} />{label}</div>;
}
export function ErrorState({ message, retry }) {
  return <div className="state-box state-error" role="alert"><AlertCircle size={18} /><span>{message || 'The backend could not be reached.'}</span>{retry && <button className="button button-quiet" onClick={retry}>Retry</button>}</div>;
}
export function EmptyState({ title = 'No dataset available', children }) {
  return <div className="empty-state"><span className="empty-icon"><Database size={20} /></span><strong>{title}</strong><p>{children || 'Dataset not available — upload the required CSV files.'}</p></div>;
}
export function Panel({ title, subtitle, action, children, className = '' }) {
  return <section className={`panel ${className}`}><div className="panel-heading"><div><h2>{title}</h2>{subtitle && <p>{subtitle}</p>}</div>{action}</div>{children}</section>;
}
export function PageHeader({ eyebrow = 'SHOPSENSE AI', title, description, action }) {
  return <div className="page-heading"><div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1><p>{description}</p></div>{action}</div>;
}
