import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { api } from '../services/api.js';
import { renderApp } from './test-utils.jsx';

beforeEach(() => {
  vi.spyOn(api, 'health').mockResolvedValue({ status: 'ok' });
  vi.spyOn(api, 'customerSummary').mockResolvedValue({ status: 'missing_inputs', customer_count: null, segment_counts: [], churn_risk_distribution: {}, missing_files: ['customers.csv', 'orders.csv'] });
  vi.spyOn(api, 'ticketSummary').mockResolvedValue({ status: 'missing_inputs', ticket_rows: null, category_counts: {}, priority_counts: {} });
  vi.spyOn(api, 'database').mockResolvedValue({ exists: false, table_count: 0, tables: {} });
  vi.spyOn(api, 'availability').mockResolvedValue({ dataset_count: 0, available: { 'customers.csv': false, 'orders.csv': false, 'tickets.csv': false }, missing: ['customers.csv', 'orders.csv', 'tickets.csv'] });
  vi.spyOn(api, 'profiling').mockResolvedValue({ status: 'missing_inputs', datasets: {} });
  vi.spyOn(api, 'eda').mockResolvedValue({ chart_count: 0, charts: [] });
  vi.spyOn(api, 'customerRfm').mockResolvedValue({ status: 'missing_inputs', rfm_summary: null });
  vi.spyOn(api, 'customerSegments').mockResolvedValue({ status: 'missing_inputs', segments: [] });
  vi.spyOn(api, 'customerRisk').mockResolvedValue({ status: 'missing_inputs', churn_risk: null });
  vi.spyOn(api, 'customerEvaluation').mockResolvedValue({ status: 'missing_inputs', evaluations: [] });
  vi.spyOn(api, 'assistantHealth').mockResolvedValue({ status: 'ok', policy_documents: 8, indexed_chunks: 25, llm_mode: 'deterministic_mock', vector_backend: 'sqlite_cosine_fallback' });
});

describe('ShopSense dashboard', () => {
  it('renders overview without inventing customer metrics when datasets are absent', async () => {
    renderApp();
    expect((await screen.findAllByText('Dataset not available — upload the required CSV files.')).length).toBeGreaterThan(0);
    expect(screen.getByText('No revenue aggregate API is available')).toBeInTheDocument();
    expect(screen.getByText('Customer Intelligence')).toBeInTheDocument();
  });

  it('navigates between dashboard pages', async () => {
    const user = userEvent.setup(); renderApp();
    await user.click(screen.getByRole('link', { name: /Data Quality/i }));
    expect(await screen.findByRole('heading', { name: 'Data Quality Center' })).toBeInTheDocument();
    await user.click(screen.getByRole('link', { name: /Customer Intelligence/i }));
    expect(await screen.findByRole('heading', { name: 'Customer Intelligence' })).toBeInTheDocument();
  });

  it('shows clear ticket validation errors for empty and oversized text', async () => {
    const validateSpy = vi.spyOn(api, 'validateTicket');
    const user = userEvent.setup(); renderApp('/support');
    const button = await screen.findByRole('button', { name: 'Validate & classify' });
    await user.click(button);
    expect(screen.getByRole('alert')).toHaveTextContent('Enter a ticket message');
    fireEvent.change(screen.getByLabelText('Customer message'), { target: { value: 'x'.repeat(20001) } });
    await user.click(button);
    expect(screen.getByRole('alert')).toHaveTextContent('maximum is 20,000 characters');
    expect(validateSpy).not.toHaveBeenCalled();
  });

  it('does not render a raw ticket identifier in classification results', async () => {
    vi.spyOn(api, 'validateTicket').mockResolvedValue({ valid: true });
    vi.spyOn(api, 'classifyTicket').mockResolvedValue({ accepted: true, status: 'classified', category: 'REFUND', priority: 'MEDIUM', team: 'Refunds', rationale: 'Masked safely.', pii_mask_counts: { order_id: 1 } });
    const user = userEvent.setup(); renderApp('/support');
    await user.type(await screen.findByLabelText('Customer message'), 'My order ORD123456 is late');
    await user.click(screen.getByRole('button', { name: 'Validate & classify' }));
    expect(await screen.findByText('Refund')).toBeInTheDocument();
    expect(screen.queryByText('ORD123456')).not.toBeInTheDocument();
  });

  it('keeps assistant conversation masked and displays citations and refund simulation status', async () => {
    vi.spyOn(api, 'chat').mockResolvedValue({ status: 'answered', conversation_id: 'abc', answer: 'See the synthetic policy. No action has been performed.', citations: ['refund_policy.md#general-review'], requires_human_review: true });
    vi.spyOn(api, 'refund').mockResolvedValue({ status: 'human_review_required', conversation_id: 'abc', refund_state: 'HUMAN_REVIEW', policy_guidance: 'A human must review this request.', citations: ['refund_policy.md#general-review'], requires_human_review: true, simulated_only: true, refund_executed: false, message: 'No real refund was approved or processed.' });
    const user = userEvent.setup(); renderApp('/assistant');
    await user.type(await screen.findByRole('textbox', { name: 'Message' }), 'Please check ORD123456');
    await user.click(screen.getByRole('button', { name: 'Send message' }));
    expect(await screen.findByText('refund_policy.md#general-review')).toBeInTheDocument();
    expect(sessionStorage.getItem('shopsense-assistant-session-v1')).not.toContain('ORD123456');
    await user.click(screen.getByRole('button', { name: 'Start refund assistance' }));
    expect(await screen.findByText(/Simulated refund workflow · HUMAN_REVIEW/)).toBeInTheDocument();
    expect(screen.getAllByText(/No real refund was approved or processed/).length).toBeGreaterThan(0);
  });
});
