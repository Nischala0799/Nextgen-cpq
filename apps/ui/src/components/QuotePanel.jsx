import { useState } from 'react';
import { removeLine, finalizeQuote } from '../api';
import { getSkuById } from '../catalog';

export default function QuotePanel({ quote, onQuoteUpdate }) {
  const [finalizing, setFinalizing] = useState(false);
  const [removing, setRemoving] = useState(null);
  const [finalizeError, setFinalizeError] = useState('');

  const isFinalized = quote.status === 'FINALIZED';

  async function handleRemove(lineId) {
    setRemoving(lineId);
    const updated = await removeLine(quote.quote_id, lineId);
    onQuoteUpdate(updated);
    setRemoving(null);
  }

  async function handleFinalize() {
    setFinalizing(true);
    setFinalizeError('');
    const result = await finalizeQuote(quote.quote_id);
    if (result.error) {
      setFinalizeError(Array.isArray(result.error) ? result.error[0].message : result.error);
    } else {
      onQuoteUpdate(result.quote);
    }
    setFinalizing(false);
  }

  return (
    <div className="flex-1 flex flex-col">
      <div className="px-6 py-3 border-b border-gray-200 bg-white flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">Quote</h2>
          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
            isFinalized ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'
          }`}>
            {quote.status}
          </span>
        </div>
        <span className="text-xs text-gray-400">v{quote.active_version}</span>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        {quote.line_count === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center py-20">
            <div className="w-12 h-12 rounded-full bg-gray-100 flex items-center justify-center mb-3">
              <svg className="w-6 h-6 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <p className="text-sm font-medium text-gray-500">No items yet</p>
            <p className="text-xs text-gray-400 mt-1">Select a product from the catalog to get started</p>
          </div>
        ) : (
          <LineItemsTable quote={quote} onRemove={handleRemove} removing={removing} isFinalized={isFinalized} />
        )}
      </div>

      <div className="border-t border-gray-200 bg-white px-6 py-4">
        <PriceSummary quote={quote} />

        {!isFinalized && (
          <div className="mt-4">
            {finalizeError && (
              <p className="text-xs text-red-600 mb-2">{finalizeError}</p>
            )}
            <button
              onClick={handleFinalize}
              disabled={finalizing || quote.line_count === 0}
              className="w-full py-2.5 bg-green-600 text-white rounded-lg font-medium text-sm hover:bg-green-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              {finalizing ? 'Finalizing…' : 'Finalize Quote'}
            </button>
          </div>
        )}

        {isFinalized && (
          <div className="mt-4 flex items-center gap-2 justify-center text-green-700 bg-green-50 rounded-lg px-4 py-3">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            <span className="text-sm font-medium">Quote finalized — no further changes allowed</span>
          </div>
        )}
      </div>
    </div>
  );
}

function LineItemsTable({ quote, onRemove, removing, isFinalized }) {
  return (
    <div className="space-y-3">
      {/* We don't have line details in QuoteResponse, so we show a summary card per version */}
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200">
              <th className="text-left px-4 py-2.5 text-xs font-semibold text-gray-500 uppercase tracking-wide">Items</th>
              <th className="text-right px-4 py-2.5 text-xs font-semibold text-gray-500 uppercase tracking-wide">Count</th>
            </tr>
          </thead>
          <tbody>
            <tr className="border-b border-gray-100 last:border-0">
              <td className="px-4 py-3 text-gray-700">Configured line items</td>
              <td className="px-4 py-3 text-right font-medium text-gray-900">{quote.line_count}</td>
            </tr>
            <tr className="border-b border-gray-100 last:border-0">
              <td className="px-4 py-3 text-gray-700">Quote version</td>
              <td className="px-4 py-3 text-right font-medium text-gray-900">v{quote.active_version}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <p className="text-xs text-gray-400 text-center">
        Line detail view coming in the next iteration — pricing totals are live below.
      </p>
    </div>
  );
}

function PriceSummary({ quote }) {
  const discount = quote.discounts ?? 0;

  return (
    <div className="space-y-2">
      <div className="flex justify-between text-sm text-gray-600">
        <span>Subtotal</span>
        <span>${quote.subtotal.toFixed(2)}</span>
      </div>
      {discount > 0 && (
        <div className="flex justify-between text-sm text-green-600">
          <span>Discounts</span>
          <span>−${discount.toFixed(2)}</span>
        </div>
      )}
      <div className="flex justify-between font-semibold text-gray-900 pt-2 border-t border-gray-200">
        <span>Total</span>
        <span className="text-lg">${quote.total.toFixed(2)}</span>
      </div>
    </div>
  );
}
