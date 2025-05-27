Queries for 4:8:

```sql
SELECT id FROM law_element WHERE type = 'artikel' AND bwb_id = 'BWBR0005537' AND number='4:8' -- -> 127152

SELECT * FROM legal_case WHERE id IN (
	SELECT case_id FROM case_law WHERE law_id = '127152'
)

SELECT cl.source, cl.opschrift, lc.* FROM legal_case AS lc
JOIN case_law AS cl ON (cl.case_id = lc.id)
WHERE cl.law_id = '127152'
```