# Cascadia

Go CSS selector command line tool for HTML extraction and testing CSS selectors without writing Go code.

- Website: https://github.com/suntong/cascadia/wiki
- Source: https://github.com/suntong/cascadia
- License: MIT
- Build system: Go
- Category: web scraper / HTML extraction CLI

## Description

Cascadia started as a thin wrapper around the Go `andybalholm/cascadia`
CSS selector package and grew into a tool for testing CSS selectors from the
command line. It supports a none-block selection mode (HTML or text output)
and a block selection mode that splits matched blocks into pieces
(`RAW` / `ATTR` / `GOQR` / text) rendered as a TSV/CSV table.
