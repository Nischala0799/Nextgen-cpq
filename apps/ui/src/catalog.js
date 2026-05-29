export const CATALOG = {
  products: [
    {
      product_id: 'prod-001',
      name: 'Cloud Storage',
      skus: [
        {
          sku_id: 'sku-storage-basic',
          name: 'Basic Storage',
          base_price: 49.00,
          attributes: [
            { key: 'storage_gb', label: 'Storage (GB)', type: 'NUMBER', required: true },
          ],
        },
        {
          sku_id: 'sku-storage-pro',
          name: 'Pro Storage',
          base_price: 99.00,
          attributes: [
            { key: 'storage_gb', label: 'Storage (GB)', type: 'NUMBER', required: true },
            { key: 'region', label: 'Region', type: 'ENUM', required: true, enum_values: ['us-east', 'us-west', 'eu-central'] },
          ],
        },
      ],
    },
    {
      product_id: 'prod-002',
      name: 'Support Package',
      skus: [
        { sku_id: 'sku-support-standard', name: 'Standard Support', base_price: 29.00, attributes: [] },
        { sku_id: 'sku-support-premium', name: 'Premium Support', base_price: 79.00, attributes: [] },
      ],
    },
  ],
};

export function getAllSkus() {
  return CATALOG.products.flatMap(p => p.skus.map(s => ({ ...s, product_name: p.name })));
}

export function getSkuById(skuId) {
  return getAllSkus().find(s => s.sku_id === skuId);
}
