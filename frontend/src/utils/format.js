export const number = (value) => value == null || !Number.isFinite(Number(value)) ? '—' : Number(value).toLocaleString();
export const currency = (value) => value == null || !Number.isFinite(Number(value)) ? '—' : new Intl.NumberFormat(undefined, { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(Number(value));
export const titleCase = (value = '') => String(value).replaceAll('_', ' ').toLowerCase().replace(/\b\w/g, (letter) => letter.toUpperCase());

export function datasetAvailable(data) {
  if (!data) return false;
  return !['missing_inputs', 'missing_data', 'not_processed', 'insufficient_data'].includes(data.status);
}
