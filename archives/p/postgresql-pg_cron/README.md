# postgresql-pg_cron

pg_cron is a PostgreSQL extension that allows running cron-like scheduled jobs from within PostgreSQL. It runs as a background worker process and uses the same syntax as regular cron, but jobs are executed within the database.

## Key Features
- Schedule PostgreSQL commands using cron syntax
- Jobs execute within the database context
- Background worker process (no external scheduler needed)
- Supports per-database job scheduling

## Version 1.6.7
- Compiled for OpenHarmony / HarmonyOS (aarch64)
- Build system: PGXS (PostgreSQL Extension Building Infrastructure)
- Requires PostgreSQL 17.10

## Installation
```sql
CREATE EXTENSION pg_cron;
```

## Usage
```sql
-- Schedule a vacuum to run every day at 3:30am
SELECT cron.schedule('30 3 * * *', 'VACUUM');

-- Schedule a query to run every Saturday at 9:00am
SELECT cron.schedule('0 9 * * 6', 'DELETE FROM events WHERE event_date < now() - interval ''1 week''');
```