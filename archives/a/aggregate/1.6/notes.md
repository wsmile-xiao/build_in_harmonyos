# aggregate 1.6

## Source

The package uses the official ISC aggregate 1.6 release archive. Its SHA-256
is cross-checked against Debian's source-package metadata.

## Build

Aggregate 1.6 is a legacy Autotools project that produces the `aggregate` and
`aggregate-ios` command-line programs. It provides no upstream test target.

## Consumer test

The test supplies two adjacent `/25` prefixes and a separate `/24` prefix. It
asserts that the adjacent prefixes are merged into `192.0.2.0/24` while the
independent prefix remains in the output.

## Platform constraint

The initial HarmonyOS adaptation is restricted to armv8. True-device validation
on ohos-aarch64 passed on 2026-08-07.
