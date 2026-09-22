-- Received batches whose expiry date falls within the given horizon.
-- Params (in order): as_of date, horizon end date. Already-expired batches
-- (expiry_date < as_of) are excluded, not flagged as "at risk".
SELECT
    c.name AS chemical_name,
    l.name AS location_name,
    m.batch_number AS batch_number,
    m.expiry_date AS expiry_date
FROM stock_movements m
JOIN dim_chemical c ON c.chemical_id = m.chemical_id
JOIN dim_lab_location l ON l.location_id = m.location_id
WHERE m.movement_type = 'RECEIPT'
  AND m.expiry_date IS NOT NULL
  AND m.expiry_date BETWEEN ? AND ?
ORDER BY m.expiry_date ASC;
