# GCC Ada 9.5.0 and AdaCGI 1.6 linkage validation

## Purpose

This test closes a real downstream linkage path inside the `gcc-ada/9.5.0`
package validation:

```text
packaged gcc-ada/9.5.0
  -> gnatmake + gnatbind + gnatlink
  -> AdaCGI 1.6 CGI/Ustrings library units
  -> signed OHOS/aarch64 consumer executable
  -> deterministic CGI request with nine assertions
```

It replaces the previous metadata-only relationship with executable evidence.
The separate `adacgi/1.6` Conan package remains subject to R36 and will only be
built after this compiler package is merged and published.

## Source provenance

- Source archive: `https://deb.debian.org/debian/pool/main/a/adacgi/adacgi_1.6.orig.tar.gz`
- Archive SHA-256: `6a417f4936a362c1d3d85b8331c26be4ef381ce152cf03c39ac1d5c86fdb884c`
- Imported upstream units: `cgi.ads`, `cgi.adb`, `ustrings.ads`, `ustrings.adb`
- License notice: `COPYING`; LGPL text: `lesser.txt`
- Semantic source changes: none; Git-normalized trailing blank lines do not
  alter Ada tokens or behavior.

The custom `test_adacgi.adb` consumer adds nine fail-closed assertions for GET
method recognition, argument and duplicate-key counts, value lookup, percent
decoding, URL encoding/decoding and HTML escaping. The direct URL decode check
uses the public `Translate_Plus => False` parameter so `%2B` is verified as a
literal plus instead of the form-decoding default that maps plus to space.

## CI behavior

`test_package/conanfile.py` resolves all GNAT tools from the tested
`gcc-ada/9.5.0` package. It compiles AdaCGI with Ada 95 mode, signs the resulting
OHOS ELF, and invokes `verify_adacgi.py` with:

```text
REQUEST_METHOD=GET
QUERY_STRING=name=HarmonyOS&name=Ada%20CGI
```

Success requires exit code zero and the exact output `adacgi smoke: ok`; the
verifier emits `ADACGI_LINKAGE=pass assertions=9`. A compile, bind, link, sign,
execution or assertion failure therefore fails `conan create` and PR CI.

The GCC 9 aggregate `gnattools` target normally builds twelve executables.
This package needs only `gnatbind`, `gnatmake`, `gnatlink`, and `gnatchop`;
the source preparation step narrows both the build and install lists to those
four tools. This preserves every packaged tool and all existing GCC/AdaCGI
tests while leaving enough of the 3600-second CI budget to execute the
downstream linkage test.

## Atomicity boundary

This is an integration test of the compiler package, not an unpublished second
Conan recipe. It keeps JC6 one-software atomicity intact and does not bypass the
R36 requirement that the completed `adacgi/1.6` recipe consume a published
`gcc-ada/9.5.0` package in its own downstream PR.
