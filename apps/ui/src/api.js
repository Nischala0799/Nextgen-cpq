const BASE = '';

export async function createQuote(customerId = null) {
  const res = await fetch(`${BASE}/quotes`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ customer_id: customerId }),
  });
  if (!res.ok) throw new Error('Failed to create quote');
  return res.json();
}

export async function getQuote(quoteId) {
  const res = await fetch(`${BASE}/quotes/${quoteId}`);
  if (!res.ok) throw new Error('Quote not found');
  return res.json();
}

export async function addLine(quoteId, payload) {
  const res = await fetch(`${BASE}/quotes/${quoteId}/lines`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  const data = await res.json();
  if (!res.ok) return { error: data.detail };
  return { quote: data };
}

export async function removeLine(quoteId, lineId) {
  const res = await fetch(`${BASE}/quotes/${quoteId}/lines/${lineId}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error('Failed to remove line');
  return res.json();
}

export async function finalizeQuote(quoteId) {
  const res = await fetch(`${BASE}/quotes/${quoteId}/finalize`, {
    method: 'POST',
  });
  const data = await res.json();
  if (!res.ok) return { error: data.detail };
  return { quote: data };
}
