# cronolog

Log rotation software: reads log messages from stdin and writes them to
a set of output files whose names are built from a strftime template
and the current date/time (e.g. Apache `TransferLog "|cronolog
/www/logs/%Y/%m/%d/access.log"`).

- Upstream: https://github.com/fordmason/cronolog
- License: GPL-2.0-or-later
- Build system: autotools

## Versions

| Version | Status | Notes |
|---------|--------|-------|
| 1.6.2-rpk | built | Debian/Ubuntu 1.6.2+rpk 修订对应的上游 1.6.2 源码；无第三方依赖 |
