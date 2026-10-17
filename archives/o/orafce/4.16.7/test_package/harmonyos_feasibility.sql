\set ECHO none
SET client_min_messages = warning;
SET DATESTYLE TO ISO;
SET client_encoding = utf8;
\set ECHO all
SET search_path TO public, oracle;
-- HarmonyOS (OpenHarmony PC aarch64) consumer-feasibility case:
-- load the orafce extension and exercise core Oracle-compatibility
-- functions to demonstrate the extension works as a real consumer.
-- Functions live in the `oracle` schema, exposed via search_path.
SELECT nvl(NULL::text, 'harmonyos-ok') AS nvl_test;
SELECT decode(2, 1, 'one', 2, 'two', 'other') AS decode_test;
SELECT add_months(date '2026-01-31', 1) AS add_months_test;
SELECT months_between(date '2026-03-31', date '2026-01-31') AS months_between_test;
SELECT last_day(date '2026-02-10') AS last_day_test;
SELECT trunc(date '2026-02-15', 'MM') AS trunc_test;
