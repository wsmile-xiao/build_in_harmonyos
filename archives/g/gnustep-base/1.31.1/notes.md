# gnustep-base 1.31.1 adaptation notes

## W0 dependency check

Source package:

- URL: https://ftp.gnustep.org/pub/gnustep/core/gnustep-base-1.31.1.tar.gz
- SHA256: `e7546f1c978a7c75b676953a360194a61e921cb45a4804497b4f346a460545cd`

Direct dependencies selected for the first slice:

- `gnustep-make/2.9.2` as `tool_requires`
- `libobjc2/2.2.1`
- `libffi/3.5.2`
- `curl/8.15.0`

The source INSTALL file lists ffi, ICU, GnuTLS, libxml2, libxslt, Avahi, zlib,
iconv, OpenSSL, libcurl, and libdispatch as possible external dependencies.
For Affiche's Foundation needs, this first recipe keeps libffi/libcurl and
disables XML, XSLT, TLS, zeroconf, ICU, libdispatch, NSURLSession, and iconv.

## Source/build analysis

The upstream package is a GNUstep core library with:

- top-level `configure`
- top-level `GNUmakefile`
- `Source`, `Tools`, `NSTimeZones`, `Resources`, and `Tests` subprojects
- native GNUstep installation layout under `Library/Headers`,
  `Library/Libraries`, and `Tools`

`configure` errors out if `GNUSTEP_MAKEFILES` is not available, so the recipe
derives it from the `gnustep-make` tool package and exports the matching
GNUstep environment while configuring, building, and installing.

## Test package

`test_package` compiles a real Objective-C Foundation consumer. It creates
`NSString`, `NSArray`, `NSData`, and `NSDictionary` objects through
`Foundation/Foundation.h`, links against `gnustep-base::gnustep-base`, and runs
the executable when the target can run.

## Path B knowledge drafts

This adaptation contributes two task-local knowledge drafts for later GNUstep
ports such as `gnustep-gui` and `affiche`:

- `knowledge/drafts/DRAFT-gnustep-base-1.31.1-gnumake-env.kv` and `.md`:
  GNUstep Make domain/environment closure for OHOS Conan recipes.
- `knowledge/drafts/DRAFT-gnustep-base-1.31.1-objc-runtime-consumer.kv` and
  `.md`: Objective-C runtime flags, runtime library paths, and Foundation
  consumer verification for GNUstep packages.

## Local validation

Prepared on Windows host only. Conan is not installed in this local desktop
environment, so `conan create` was not run here.

## Next commands

```sh
conan download "gnustep-make/2.9.2" -r=ohpcd --only-recipe
conan download "libobjc2/2.2.1" -r=ohpcd --only-recipe
conan download "libffi/3.5.2" -r=ohpcd --only-recipe
conan download "curl/8.15.0" -r=ohpcd --only-recipe
CI_PACKAGES="archives/g/gnustep-base/1.31.1" zsh ci/conan/build_and_test.sh
```
