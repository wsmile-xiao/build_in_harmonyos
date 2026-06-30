# PostgreSQL URL Encode

URL encoding and decoding functions for PostgreSQL.

## Description

This PostgreSQL extension provides functions for URL encoding and decoding text, useful for web applications and data processing.

## Features

- `url_encode(text)` - Encode text for safe URL transmission
- `url_decode(text)` - Decode URL-encoded text
- Support for UTF-8 encoding
- Compatible with PostgreSQL 9.5+

## Requirements

- PostgreSQL 9.5 or later
- PostgreSQL development headers

## Installation

### Using PGXS (recommended)

```bash
make
make install
```

### Manual installation

```sql
CREATE EXTENSION url_encode;
```

## Usage

```sql
-- Encode a URL
SELECT url_encode('Hello World!');

-- Decode a URL
SELECT url_decode('Hello%20World%21');
```

## Links

- PGXN: https://api.pgxn.org/dist/url_encode/
- Documentation: https://api.pgxn.org/dist/url_encode/