# libevent 2.1.13 test report

## Scope

- Date: 2026-08-01
- Source: official `release-2.1.13-stable` archive
- Delivery test requirement: `zlib/1.3.1.1`

## Upstream Test Result

The official upstream CTest suite passed `49/49`.

## Recipe Closure Status

The frozen execution tree
`362cad634f1f34dc82b4cf18e915a6d38c7ee5c5` was frozen as candidate SHA256
`a9aae71f1f362638ff287fae1d50a9e51999875138d7eddfba43c25892fb5c5e`.
All six patches replay against the official archive through Git on
LF-normalized inputs and Conan's `patch-ng` backend with `fuzz=False`; the
resulting 221-file source trees are byte-identical. A fresh `conan create`
completed successfully with log SHA256
`375e793e8c9cb89e35d9e8d2c42c51e3756392d98f65e82645ac2af0f04d630f`.

- The POLL and EPOLL capability failures were corrected in production source.
- The three test-harness portability changes preserve or strengthen assertions.
- `event-config.h` contains `#define EVENT__HAVE_LIBZ 1`.

## Installed-package Validation

Package creation and the installed-package consumers completed successfully.

## Boundary

The frozen candidate and clean recipe closure are complete. Current-HEAD AI
Review and Buildbot remain PR-stage gates.
