import { useState } from 'react';
import CatalogPanel from './components/CatalogPanel';
import QuotePanel from './components/QuotePanel';
import { createQuote } from './api';
import './index.css';

export default function App() {
  const [quote, setQuote] = useState(null);
  const [starting, setStarting] = useState(false);

  async function handleStart() {
    setStarting(true);
    try {
      const q = await createQuote();
      setQuote(q);
    } finally {
      setStarting(false);
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">NextGen CPQ</h1>
          <p className="text-sm text-gray-500">Configure · Price · Quote</p>
        </div>
        {quote && (
          <span className="text-xs font-mono text-gray-400">
            Quote {quote.quote_id.slice(0, 8)}…
          </span>
        )}
      </header>

      {!quote ? (
        <div className="flex flex-col items-center justify-center min-h-[70vh] gap-4">
          <h2 className="text-2xl font-semibold text-gray-800">Build a Quote</h2>
          <p className="text-gray-500 text-sm">Select products, configure options, and generate a priced quote.</p>
          <button
            onClick={handleStart}
            disabled={starting}
            className="mt-2 px-6 py-3 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors"
          >
            {starting ? 'Creating…' : 'New Quote'}
          </button>
        </div>
      ) : (
        <div className="flex min-h-[calc(100vh-65px)]">
          <CatalogPanel quote={quote} onQuoteUpdate={setQuote} />
          <QuotePanel quote={quote} onQuoteUpdate={setQuote} />
        </div>
      )}
    </div>
  );
}
