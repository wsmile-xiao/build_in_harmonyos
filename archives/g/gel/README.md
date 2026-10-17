# gel

A modern gem manager for Ruby.

## Description

gel is a minimal package manager for the Ruby programming language. It provides
commands for installing, locking, and executing Ruby gems as an alternative to
Bundler.

## Upstream

- **Homepage**: https://gel.dev
- **Repository**: https://github.com/gel-rb/gel
- **License**: MIT

## Build System

gel is a pure Ruby script tool. No compilation is required. The build process
consists of copying the `exe/gel` script and `lib/` directory into the Conan
package. Man pages are generated from `.ronn` sources using `ronn` if available.

## OHOS Adaptation

- **Build system**: script (no compilation)
- **Shebang**: `#!/usr/bin/env ruby --disable=gems` (OHOS-compatible if Ruby installed)
- **Dependencies**: Ruby runtime (not a Conan dependency, system-provided)
- **Man pages**: Generated from `.ronn` files using ronn; skipped if ronn unavailable
