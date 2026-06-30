# pgexportdoc

CLI tool for exporting XML, TEXT and BYTEA documents from PostgreSQL.

## Description

pgexportdoc is a PostgreSQL client utility that exports XML, JSON, TEXT, and BYTEA documents from a PostgreSQL database to files or stdout. It connects to a PostgreSQL server using libpq and retrieves document data from SQL queries.

## Usage

```bash
pgexportdoc -c 'select x from xmldata where id = 1' -t XML -f myxmldoc.xml "dbname"
```

## Options

- `-c COMMAND` - SQL query to execute
- `-t TYPE` - Document type: XML, TEXT, or BYTEA
- `-f FILE` - Output filename (default: stdout)
- `-V, --version` - Show version information
- `-?, --help` - Show help

## Dependencies

- PostgreSQL (libpq)
- libxml2 (optional, for XML documents)

## Author

Pavel Stehule (pavel.stehule@gmail.com)

## License

BSD-2-Clause
