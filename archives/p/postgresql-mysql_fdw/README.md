# postgresql-mysql_fdw

MySQL Foreign Data Wrapper for PostgreSQL — allows PostgreSQL to access MySQL/MariaDB databases as foreign tables.

## Description

mysql_fdw is a PostgreSQL extension that implements a Foreign Data Wrapper (FDW) for MySQL/MariaDB servers. It enables PostgreSQL to query, insert, update, and delete data on a MySQL/MariaDB server as if the remote tables were local PostgreSQL tables.

## Key Features

- SELECT, INSERT, UPDATE, DELETE on MySQL/MariaDB tables
- WHERE clause pushdown
- JOIN pushdown (aggregates)
- Aggregate pushdown
- LIMIT/OFFSET pushdown
- Column pushdown
- Connection pooling and management

## Dependencies

- PostgreSQL >= 13 (uses PGXS build system)
- MariaDB Connector/C or MySQL client library (provides `mysql_config`)

## Building

```bash
make USE_PGXS=1
make USE_PGXS=1 install
```

## Usage

```sql
CREATE EXTENSION mysql_fdw;
CREATE SERVER mysql_server FOREIGN DATA WRAPPER mysql_fdw OPTIONS (host 'localhost', port '3306');
CREATE USER MAPPING FOR current_user SERVER mysql_server OPTIONS (username 'root', password 'secret');
CREATE FOREIGN TABLE mysql_table (id int, name text) SERVER mysql_server OPTIONS (dbname 'testdb', table_name 'test_table');
```

## License

PostgreSQL License (similar to BSD/MIT)