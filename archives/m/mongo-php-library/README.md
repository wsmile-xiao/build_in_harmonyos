# mongo-php-library

## What is it?

mongo-php-library (officially `mongodb/mongodb`) is the MongoDB PHP driver library. It provides a high-level API for MongoDB operations on top of the low-level MongoDB PHP extension (`ext-mongodb`).

## Key Features

- Pure PHP library — no compilation required
- PSR-4 autoloading (MongoDB namespace → src/)
- Supports MongoDB CRUD operations, aggregation pipelines, change streams, GridFS
- Requires PHP 8.1+ and the ext-mongodb PHP extension (v2.3+)

## OHOS/HarmonyOS Adaptation

### Build System
- **Type**: script (pure PHP library)
- **No configure/make/install required** — source PHP files are directly installed

### Installation
PHP files are installed to `$PREFIX/share/php/mongodb/`:
- `src/*.php` (492 PHP class/function files)
- `composer.json` (PSR-4 autoloading configuration)

### Runtime Dependencies
- php >= 8.1
- ext-mongodb >= 2.3 (MongoDB PHP extension — must be installed separately)
- psr/log ^1.1.4|^2|^3
- symfony/polyfill-php85 ^1.33

### Notes
- No patches required — pure PHP, no source modifications needed
- The library itself cannot function without the ext-mongodb PHP extension

## Version 2.3.0

- Status: built
- Build date: 2026-06-08
- No compilation issues encountered