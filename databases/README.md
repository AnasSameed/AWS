# AWS Databases: Aurora, RDS and DynamoDB (practice)

Notes: [AWS_Databases_Aurora_Basics.pdf](../notes/AWS_Databases_Aurora_Basics.pdf)
(also see [AWS_Route53_DNS_Aurora_Notes.pdf](../notes/AWS_Route53_DNS_Aurora_Notes.pdf) for Aurora endpoints, failover and labs).

## What is here

A small **synthetic** clinical-trial database (sites, subjects, visits, adverse events). No real patient data.

| File | Purpose |
|---|---|
| `sql/01_schema.sql` | Tables, primary and foreign keys, CHECK constraints, indexes |
| `sql/02_data.sql` | Seeded synthetic rows (24 subjects, 72 visits, 20 adverse events) |
| `sql/03_queries.sql` | 7 practice queries: GROUP BY, JOIN, LEFT JOIN, HAVING, window function |
| `sql/run_sqlite.py` | Loads everything into SQLite and prints each query's result |

## Run it (free, on your laptop)

```
python sql/run_sqlite.py
```

## Run it on Aurora MySQL (costs money; delete the cluster afterwards)

```
mysql -h <cluster-endpoint> -u admin -p < sql/01_schema.sql
mysql -h <cluster-endpoint> -u admin -p < sql/02_data.sql
mysql -h <cluster-endpoint> -u admin -p < sql/03_queries.sql
```

The same files run on MySQL 8 / Aurora MySQL and on SQLite. The SQLite run was tested; the Aurora run was not.

## Things to try

- Guess each query's result before running it.
- Turn query 5's LEFT JOIN into an INNER JOIN and see which subjects disappear.
- Uncomment query 8 (age 12) and watch the constraint refuse it.
- On MySQL/Aurora, run `EXPLAIN` on query 9 with and without the index.
