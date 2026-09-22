-- Total quantity of each chemical used, by month.
SELECT
    c.name AS chemical_name,
    d.year AS year,
    d.month AS month,
    ROUND(SUM(-m.quantity), 3) AS total_used
FROM stock_movements m
JOIN dim_chemical c ON c.chemical_id = m.chemical_id
JOIN dim_date d ON d.date_id = m.date_id
WHERE m.movement_type = 'USAGE'
GROUP BY c.name, d.year, d.month
ORDER BY c.name, d.year, d.month;
