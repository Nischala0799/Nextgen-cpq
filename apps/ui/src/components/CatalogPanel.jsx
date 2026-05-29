import { useState } from 'react';
import { CATALOG, getSkuById } from '../catalog';
import { addLine } from '../api';

export default function CatalogPanel({ quote, onQuoteUpdate }) {
  const [selectedSku, setSelectedSku] = useState(null);
  const [form, setForm] = useState({});
  const [quantity, setQuantity] = useState(1);
  const [term, setTerm] = useState('MONTHLY');
  const [discount, setDiscount] = useState('');
  const [errors, setErrors] = useState([]);
  const [adding, setAdding] = useState(false);

  function handleSelectSku(sku) {
    setSelectedSku(sku);
    setForm({});
    setErrors([]);
  }

  function handleAttrChange(key, value) {
    setForm(f => ({ ...f, [key]: value }));
  }

  async function handleAdd() {
    setAdding(true);
    setErrors([]);
    const attrs = {};
    for (const [k, v] of Object.entries(form)) {
      const attrDef = selectedSku.attributes.find(a => a.key === k);
      if (attrDef?.type === 'NUMBER') attrs[k] = Number(v);
      else attrs[k] = v;
    }
    const payload = {
      sku_id: selectedSku.sku_id,
      quantity: Number(quantity),
      term,
      selected_attributes: attrs,
      ...(discount ? { discount_amount: Number(discount) } : {}),
    };
    const result = await addLine(quote.quote_id, payload);
    if (result.error) {
      setErrors(Array.isArray(result.error) ? result.error : [{ message: result.error }]);
    } else {
      onQuoteUpdate(result.quote);
      setSelectedSku(null);
      setForm({});
      setQuantity(1);
      setTerm('MONTHLY');
      setDiscount('');
    }
    setAdding(false);
  }

  return (
    <div className="w-80 bg-white border-r border-gray-200 flex flex-col">
      <div className="px-4 py-3 border-b border-gray-200">
        <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">Product Catalog</h2>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {CATALOG.products.map(product => (
          <div key={product.product_id}>
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">{product.name}</p>
            <div className="space-y-2">
              {product.skus.map(sku => (
                <button
                  key={sku.sku_id}
                  onClick={() => handleSelectSku(sku)}
                  disabled={quote.status === 'FINALIZED'}
                  className={`w-full text-left px-3 py-3 rounded-lg border transition-colors ${
                    selectedSku?.sku_id === sku.sku_id
                      ? 'border-indigo-500 bg-indigo-50'
                      : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                  } disabled:opacity-40 disabled:cursor-not-allowed`}
                >
                  <div className="flex justify-between items-start">
                    <span className="text-sm font-medium text-gray-800">{sku.name}</span>
                    <span className="text-sm font-semibold text-indigo-600">${sku.base_price}/mo</span>
                  </div>
                  {sku.attributes.length > 0 && (
                    <p className="text-xs text-gray-400 mt-1">{sku.attributes.map(a => a.label).join(', ')}</p>
                  )}
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>

      {selectedSku && (
        <div className="border-t border-gray-200 p-4 space-y-3 bg-gray-50">
          <p className="text-sm font-semibold text-gray-700">Configure: {selectedSku.name}</p>

          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-xs text-gray-500 mb-1 block">Quantity</label>
              <input
                type="number"
                min="1"
                value={quantity}
                onChange={e => setQuantity(e.target.value)}
                className="w-full border border-gray-200 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-indigo-400"
              />
            </div>
            <div>
              <label className="text-xs text-gray-500 mb-1 block">Term</label>
              <select
                value={term}
                onChange={e => setTerm(e.target.value)}
                className="w-full border border-gray-200 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-indigo-400"
              >
                <option value="MONTHLY">Monthly</option>
                <option value="ANNUAL">Annual (−15%)</option>
              </select>
            </div>
          </div>

          {selectedSku.attributes.map(attr => (
            <div key={attr.key}>
              <label className="text-xs text-gray-500 mb-1 block">
                {attr.label}{attr.required && <span className="text-red-400 ml-0.5">*</span>}
              </label>
              {attr.type === 'ENUM' ? (
                <select
                  value={form[attr.key] || ''}
                  onChange={e => handleAttrChange(attr.key, e.target.value)}
                  className="w-full border border-gray-200 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-indigo-400"
                >
                  <option value="">Select…</option>
                  {attr.enum_values.map(v => <option key={v} value={v}>{v}</option>)}
                </select>
              ) : (
                <input
                  type={attr.type === 'NUMBER' ? 'number' : 'text'}
                  value={form[attr.key] || ''}
                  onChange={e => handleAttrChange(attr.key, e.target.value)}
                  className="w-full border border-gray-200 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-indigo-400"
                />
              )}
            </div>
          ))}

          <div>
            <label className="text-xs text-gray-500 mb-1 block">Discount ($) — optional</label>
            <input
              type="number"
              min="0"
              value={discount}
              onChange={e => setDiscount(e.target.value)}
              placeholder="0.00"
              className="w-full border border-gray-200 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-indigo-400"
            />
          </div>

          {errors.length > 0 && (
            <div className="space-y-1">
              {errors.map((e, i) => (
                <p key={i} className="text-xs text-red-600 bg-red-50 px-2 py-1 rounded">{e.message}</p>
              ))}
            </div>
          )}

          <div className="flex gap-2">
            <button
              onClick={handleAdd}
              disabled={adding}
              className="flex-1 py-2 bg-indigo-600 text-white text-sm rounded-lg font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors"
            >
              {adding ? 'Adding…' : 'Add to Quote'}
            </button>
            <button
              onClick={() => { setSelectedSku(null); setErrors([]); }}
              className="px-3 py-2 border border-gray-200 text-gray-600 text-sm rounded-lg hover:bg-gray-100 transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
