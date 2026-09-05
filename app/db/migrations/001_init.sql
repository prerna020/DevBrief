CREATE TABLE IF NOT EXISTS processed_deliveries (
    delivery_id TEXT PRIMARY KEY,
    processed_at TIMESTAMPTZ DEFAULT now()
);
