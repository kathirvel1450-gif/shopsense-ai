import { useEffect, useState } from 'react';
import { AlertTriangle, ArrowUp, Bot, FileText, RotateCcw, ShieldCheck, Sparkles, UserRound } from 'lucide-react';
import { api } from '../services/api.js';
import { useConversation, maskDisplayText } from '../hooks/ConversationContext.jsx';
import { ErrorState, LoadingState, PageHeader } from '../components/common/States.jsx';

const suggestions = ['What does the demonstration refund policy say?', 'My delivery is delayed. What can I do?', 'How are missing items handled?'];

export default function AIAssistant() {
  const session = useConversation(); const [health, setHealth] = useState(null); const [healthError, setHealthError] = useState(''); const [loadingHealth, setLoadingHealth] = useState(true); const [input, setInput] = useState(''); const [busy, setBusy] = useState(false); const [error, setError] = useState('');
  const messages = session?.messages || [];
  useEffect(() => { let live = true; api.assistantHealth().then((data) => live && setHealth(data)).catch((e) => live && setHealthError(e.message)).finally(() => live && setLoadingHealth(false)); return () => { live = false; }; }, []);
  const addMessage = (message) => session.update((current) => ({ ...current, messages: [...current.messages, { ...message, id: `${Date.now()}-${Math.random()}` }] }));
  async function send(kind = 'chat', questionOverride = null) {
    const question = questionOverride ?? input;
    if (!question.trim() || busy) return;
    setError(''); setBusy(true); setInput(''); addMessage({ role: 'user', text: maskDisplayText(question) });
    try {
      const result = kind === 'refund' ? await api.refund(question, session.conversationId) : await api.chat(question, session.conversationId);
      if (result.conversation_id && result.conversation_id !== session.conversationId) session.update((current) => ({ ...current, conversationId: result.conversation_id }));
      if (result.status === 'rejected') throw new Error(result.rejection_reason || 'The request failed input validation.');
      addMessage({ role: 'assistant', text: result.policy_guidance || result.answer || 'A support agent should review this request.', citations: result.citations || [], requiresHuman: Boolean(result.requires_human_review), refund: kind === 'refund' ? { state: result.refund_state, simulated: result.simulated_only, executed: result.refund_executed, message: result.message } : null, status: result.status });
    } catch (reason) { setError(reason.message || 'Assistant service unavailable.'); addMessage({ role: 'assistant', text: reason.message || 'Assistant service unavailable.', error: true }); }
    finally { setBusy(false); }
  }
  async function escalate() {
    const lastUser = [...messages].reverse().find((message) => message.role === 'user');
    if (!lastUser || busy) return;
    setError(''); setBusy(true);
    try { const result = await api.escalate(lastUser.text, session.conversationId); addMessage({ role: 'assistant', text: result.created ? result.case.message : `Escalation could not be created: ${result.reason || 'request rejected'}.`, requiresHuman: true, error: !result.created }); }
    catch (reason) { setError(reason.message); }
    finally { setBusy(false); }
  }
  function reset() { if (!window.confirm('Clear this local assistant conversation?')) return; session.update({ conversationId: null, messages: [] }); setError(''); }
  const modeLabel = health?.llm_mode === 'deterministic_mock' ? 'Deterministic mock' : health?.llm_mode === 'openai_compatible' ? 'Configured model' : 'Mode unavailable';
  const noPolicies = health?.status === 'missing_policy_documents';
  return <>
    <PageHeader eyebrow="POLICY-GROUNDED SUPPORT" title="AI Assistant" description="Ask questions about the synthetic demonstration policies. Personal identifiers are masked before processing." action={<button className="button button-secondary" onClick={reset}><RotateCcw size={15} /> New conversation</button>} />
    {healthError && <ErrorState message={`Assistant health could not be loaded: ${healthError}`} />}
    {loadingHealth ? <LoadingState label="Checking assistant and policy index…" /> : <div className="assistant-runtime"><span className="runtime-pill"><span className="status-pip online" />{modeLabel}{health?.llm_mode === 'deterministic_mock' && <b>MOCK</b>}</span><span className="runtime-pill"><FileText size={13} />{health?.policy_documents ?? 0} policy sections</span><span className="runtime-pill"><ShieldCheck size={13} />{health?.vector_backend || 'Index unavailable'}</span></div>}
    {noPolicies && <div className="notice-banner notice-warning"><AlertTriangle size={17} /><span>No policy documents are indexed. Add authorized policy documents before using this assistant.</span></div>}
    <div className="assistant-layout">
      <section className="chat-panel" aria-label="Support conversation">
        <div className="chat-topline"><div className="chat-avatar"><Bot size={17} /></div><div><strong>ShopSense support</strong><small>{modeLabel} · Policy references included</small></div><span className="chat-protection"><ShieldCheck size={14} /> PII masked</span></div>
        <div className="chat-messages" aria-live="polite">
          {messages.length === 0 && <div className="chat-welcome"><span className="welcome-icon"><Sparkles size={20} /></span><h2>How can I help?</h2><p>Answers use synthetic demonstration policies. They are not actual retailer terms.</p><div className="suggestion-list">{suggestions.map((suggestion) => <button key={suggestion} onClick={() => send('chat', suggestion)} disabled={busy}>{suggestion}<ArrowUp size={13} /></button>)}</div></div>}
          {messages.map((message) => <article className={`chat-message ${message.role === 'user' ? 'from-user' : 'from-assistant'}`} key={message.id}><span className="message-avatar">{message.role === 'user' ? <UserRound size={15} /> : <Bot size={15} />}</span><div className="message-content"><div className="message-meta">{message.role === 'user' ? 'You' : 'ShopSense AI'}{message.role === 'assistant' && <span className="mock-badge">{modeLabel === 'Deterministic mock' ? 'MOCK RESPONSE' : 'POLICY RESPONSE'}</span>}</div><p>{message.text}</p>{message.refund && <div className="refund-state"><strong>Simulated refund workflow · {message.refund.state || 'HUMAN_REVIEW'}</strong><span>{message.refund.message || 'A human review is required.'}</span><b>{message.refund.executed ? 'Executed' : 'No real refund was processed'}</b></div>}{message.citations?.length > 0 && <div className="citation-list"><span>POLICY SOURCES</span>{message.citations.map((citation) => <span className="citation-chip" key={citation}><FileText size={12} />{citation}</span>)}</div>}{message.requiresHuman && <div className="human-review"><ShieldCheck size={14} /> Human review recommended</div>}</div></article>)}
          {busy && <div className="typing-indicator"><span /><span /><span /> Assistant is checking the policy context…</div>}
          {error && <div className="form-error" role="alert">{error}</div>}
        </div>
        <form className="chat-composer" onSubmit={(event) => { event.preventDefault(); send('chat'); }}><textarea aria-label="Message" value={input} onChange={(event) => setInput(event.target.value)} maxLength={20001} placeholder="Ask a question about a policy…" disabled={busy} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); send('chat'); } }} /><div className="composer-actions"><span>Do not share passwords, full card numbers or one-time codes.</span><button className="send-button" aria-label="Send message" disabled={busy || !input.trim()}><ArrowUp size={17} /></button></div></form>
      </section>
      <aside className="assistant-side"><div className="side-card"><div className="side-card-icon"><ShieldCheck size={18} /></div><h3>Safe by design</h3><p>Customer identifiers are masked before policy retrieval, prompts and conversation storage.</p><ul><li>PII masking before model calls</li><li>Answers cite retrieved sources</li><li>Refunds stop at human review</li></ul></div><div className="side-card"><div className="side-card-icon amber"><AlertTriangle size={18} /></div><h3>Need a person?</h3><p>Ask for a human handoff when the answer needs an account-specific review.</p><button className="button button-secondary side-action" onClick={escalate} disabled={busy || !messages.some((message) => message.role === 'user')}>Request human review</button></div><button className="button button-outline side-action" onClick={() => { const last = [...messages].reverse().find((message) => message.role === 'user'); if (last) send('refund', last.text); else setError('Ask a question first, then choose refund assistance.'); }} disabled={busy}>Start refund assistance</button><p className="side-disclaimer">Refund assistance is a simulation only. No order system or payment action is connected.</p></aside>
    </div>
  </>;
}
