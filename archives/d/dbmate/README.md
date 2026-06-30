# dbmate

A lightweight, zero-dependency database migration tool written in Go. Supports PostgreSQL, MySQL, SQLite, and other databases.

- **Homepage**: https://github.com/amacneil/dbmate
- **License**: MIT
- **Category**: database/migration

## Build Notes

dbmate is a pure Go tool with no C dependencies. It is built with `CGO_ENABLED=0` for static compilation, producing a single self-contained binary.
