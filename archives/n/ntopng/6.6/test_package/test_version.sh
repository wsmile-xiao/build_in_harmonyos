#!/bin/sh
# ntopng consumer smoke test — version banner.
# ntopng is a daemon that needs root + live interfaces + GeoIP data to run
# fully; the runnable headless check (and the upstream `make test` target,
# which is exactly `./ntopng --version`) is the version banner.
ntopng --version
