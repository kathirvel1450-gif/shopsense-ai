import { useEffect, useState } from 'react';
import { AlertTriangle, CheckCircle2, ClipboardCheck, Headphones, ShieldCheck } from 'lucide-react';
import { api } from '../services/api.js';
import { BarsChart, DonutChart } from '../components/charts/Charts.jsx';
import { EmptyState, ErrorState, LoadingState, PageHeader, Panel } from '../components/common/States.jsx';
import MetricCard from '../components/common/MetricCard.jsx';
import { number, titleCase } from '../utils/format.js';

const MAX_CHARS = 20000;
export default function SupportIntelligence() {
  const [summary, setSummary] = useState(null); const [summaryLoading, setSummaryLoading] = useState(true); const [error, setError] = useState('');
  const [text, setText] = useState(''); const [method, setMethod] = useState('zero_shot'); const [result, setResult] = useState(null); const [busy, setBusy] = useState(false); const [formError, setFormError] = useState('');
  const load = async () => { setSummaryLoading(true); setError(''); try { setSummary(await api.ticketSummary()); } catch (e) { setError(e.message); } finally { setSummaryLoading(false); } };
  useEffect(() => { load(); }, []);
  async function submit(action) {
    setResult(null); setFormError('');
    if (!text.trim()) { setFormError('Enter a ticket message before processing.'); return; }
    if (text.length > MAX_CHARS) { setFormError(`Ticket is too long. The maximum is ${MAX_CHARS.toLocaleString()} characters.`); return; }
    setBusy(true);
    try {
      const validation = await api.validateTicket(text);
      if (!validation.valid) { setResult({ accepted: false, rejection_reason: validation.rejection_reason, status: validation.status, pii_mask_counts: validation.pii_mask_counts }); return; }
      const response = action === 'process' ? await api.processTickets(text, method) : await api.classifyTicket(text, method);
      setResult(response);
    } catch (e) { setFormError(e.message || 'Ticket request failed.'); }
    finally { setBusy(false); }
  }
  const categories = Object.entries(summary?.category_counts || {}).map(([name, value]) => ({ name, value }));
  const priorities = Object.entries(summary?.priority_counts || {}).map(([name, value]) => ({ name, value }));
  const available = summary?.status === 'complete' || summary?.status === 'completed_with_warnings';
  return <>
    <PageHeader eyebrow="CUSTOMER SUPPORT OPERATIONS" title="Support Intelligence" description="Classify and route tickets through input validation, PII masking and guarded model calls." action={<button className="button button-secondary" onClick={load}><ClipboardCheck size={15} /> Refresh summary</button>} />
    <div className="notice-banner notice-info"><ShieldCheck size={17} /><span>Ticket text is validated and PII-masked before model processing. Results below contain classification metadata only; raw ticket text is not returned by the API.</span></div>
    {error && <ErrorState message={error} retry={load} />}
    {summaryLoading ? <LoadingState /> : <>
      <div className="metric-grid metric-grid-four"><MetricCard label="Tickets processed" value={available ? number(summary?.classified_count) : '—'} note={summary?.status === 'missing_inputs' ? 'Ticket dataset not available' : 'Aggregate API summary'} icon={Headphones} /><MetricCard label="Rejected inputs" value={available ? number(summary?.rejected_count) : '—'} note="Validation or provider failures" icon={AlertTriangle} tone="amber" /><MetricCard label="Categories observed" value={available ? number(categories.length) : '—'} note="No synthetic counts are shown" icon={ClipboardCheck} tone="teal" /><MetricCard label="Guardrail status" value="Active" note="Validation · masking · token checks" icon={ShieldCheck} tone="blue" /></div>
      <div className="content-grid support-grid">
        <Panel title="Classify a support ticket" subtitle="Input is not echoed into model results"><form onSubmit={(event) => { event.preventDefault(); submit('classify'); }}><label className="field-label" htmlFor="ticket-text">Customer message</label><textarea id="ticket-text" className="ticket-textarea" value={text} maxLength={MAX_CHARS + 1} onChange={(event) => setText(event.target.value)} placeholder="Paste a ticket message for secure validation and classification…" /><div className={`character-count ${text.length > MAX_CHARS ? 'text-error' : ''}`}>{text.length.toLocaleString()} / {MAX_CHARS.toLocaleString()} characters</div><div className="form-row"><label className="field-label" htmlFor="ticket-method">Classification prompt</label><select id="ticket-method" value={method} onChange={(event) => setMethod(event.target.value)}><option value="zero_shot">Zero-shot</option><option value="few_shot">Few-shot</option></select></div>{formError && <div className="form-error" role="alert">{formError}</div>}<div className="form-actions"><button type="submit" className="button button-primary" disabled={busy}>{busy ? 'Validating…' : 'Validate & classify'}</button><button type="button" className="button button-secondary" disabled={busy} onClick={() => submit('process')}>{busy ? 'Processing…' : 'Run process endpoint'}</button></div></form>
          {result && <div className={`ticket-result ${result.accepted ? 'result-success' : 'result-failure'}`} aria-live="polite"><div className="result-title">{result.accepted ? <><CheckCircle2 size={17} /> Classification result</> : <><AlertTriangle size={17} /> Input not processed</>}</div>{result.accepted ? <div className="result-grid"><Result label="Category" value={titleCase(result.category)} /><Result label="Priority" value={result.priority || '—'} /><Result label="Suggested team" value={result.team || '—'} /><Result label="Confidence" value={result.confidence == null ? '—' : `${Math.round(result.confidence * 100)}%`} /><Result label="Human review" value={result.requires_human_review ? 'Required' : 'Not flagged'} /><Result label="PII masks" value={Object.values(result.pii_mask_counts || {}).reduce((sum, value) => sum + value, 0)} /></div> : <p>{titleCase(result.rejection_reason || result.status || 'Request rejected')}</p>}{result.rationale && <p className="small-muted">{result.rationale}</p>}</div>}
        </Panel>
        <Panel title="Ticket categories" subtitle="Counts from the latest available summary"><DonutChart data={categories} nameKey="name" valueKey="value" empty={summary?.status === 'missing_inputs' ? 'Dataset not available — upload the required CSV files.' : 'No processed ticket category counts are available.'} /></Panel>
        <Panel title="Priority distribution" subtitle="Aggregate only"><BarsChart data={priorities} xKey="name" yKey="value" empty="No priority counts are available." color="#fbbf24" /></Panel>
        <Panel title="Routing & safety" subtitle="Transparent escalation principles"><div className="routing-list"><RouteItem priority="URGENT" team="Fraud Investigation / Payments" detail="Fraud and high-risk payment concerns require human review." /><RouteItem priority="HIGH" team="Payments" detail="Payment issues receive elevated priority and review." /><RouteItem priority="MEDIUM" team="Delivery / Refunds / Product Quality" detail="Delivery, refund and product concerns route by category." /><RouteItem priority="LOW" team="Technical Support / General Support" detail="Routine app and other issues use standard support routing." /></div></Panel>
      </div>
    </>}
  </>;
}

function Result({ label, value }) { return <div><span>{label}</span><strong>{value}</strong></div>; }
function RouteItem({ priority, team, detail }) { return <div className="route-item"><span className={`priority-tag priority-${priority.toLowerCase()}`}>{priority}</span><div><strong>{team}</strong><small>{detail}</small></div></div>; }
