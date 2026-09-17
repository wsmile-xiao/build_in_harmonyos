# libmodsecurity

ModSecurity v3 (`libmodsecurity`) is the OWASP open source, cross-platform
web application firewall (WAF) engine library. Connectors (Nginx, Apache,
IIS) consume this library to load SecRules-format rules and apply them to
HTTP transactions.

## OHOS adaptation

- Build system is GNU Autotools. The official `modsecurity-v3.0.16.tar.gz`
  release tarball already contains the generated `configure` script and the
  bundled `others/libinjection` + `others/mbedtls` sources, so no
  `build.sh`/`autoreconf` step is needed on device.
- Minimal dependency closure for R36 compliance: only `pcre2/10.40` and
  `yajl/2.1.0` (both `published` in this repository). All other optional
  ModSecurity features (`curl`, `libxml2`, `lmdb`, `lua`, `ssdeep`,
  `geoip`/`maxmind`) are explicitly disabled via `--without-*` so the
  recipe never pulls unpublished packages.
- `configure` auto-detects the OHOS host as Linux (`*-*-linux*` pattern
  matches `aarch64-unknown-linux-ohos`); no host-detection patch is carried
  in the first revision. Single-job `make -j1` is used (HMDFS jobserver).
- Upstream tests (`make check`, driven by `test/test-suite.in`) run in
  `build()`; `test_package` exercises the real C API (`msc_init`,
  `msc_create_rules_set`, `msc_rules_add`, `msc_new_transaction`,
  `msc_process_connection/uri/request/response`, `msc_intervention`).

## Dependencies

- `pcre2/10.40` (regex engine, mandatory `--with-pcre2`)
- `yajl/2.1.0` (JSON logging + test harness, mandatory `--with-yajl`)

Bundled (no Conan dependency): `libinjection`, `mbedtls` (inside the
release tarball under `others/`).

## References

- https://github.com/owasp-modsecurity/ModSecurity
- https://github.com/owasp-modsecurity/ModSecurity/releases/tag/v3.0.16
- https://modsecurity.org/
