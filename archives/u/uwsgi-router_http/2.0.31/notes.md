# uwsgi-router_http 2.0.31 adaptation notes

## Source

- Upstream: https://github.com/unbit/uwsgi
- Stable tag: 2.0.31
- Tag commit: ce518cce893d20e9c79eb2607f3a6c250468ae4d
- Source archive: https://github.com/unbit/uwsgi/archive/refs/tags/2.0.31.tar.gz
- SHA256: d5fb7b058a6e037cad1f0fb8841de56d673d80a3af036bba830143b60c67c3dc

## Build

- Builds the upstream `plugins/router_http` dynamic plugin with uWSGI's
  `uwsgiconfig.py --plugin` entry point.
- The recipe writes a local build profile under the extracted source tree:
  `pcre = true`, `routing = true`, `plugins = router_http`, and unrelated
  optional external features disabled.
- No source patches are applied.
- The plugin installs as `lib/uwsgi/router_http_plugin.so`.

## Dependencies

- The recipe requires `pcre2/10.45`.
- `routing = true` pulls uWSGI routing structs that need `uwsgi_pcre`; enabling
  `pcre = true` lets `uwsgiconfig.py` discover `pcre2-config` and define
  `UWSGI_PCRE2`.
- `plugins/router_http/uwsgiplugin.py` declares empty plugin-local `CFLAGS`,
  `LDFLAGS`, and `LIBS` lists, so the dependency is inherited from uWSGI's
  routing profile rather than from the plugin-local descriptor.
- System libraries are supplied by the target C toolchain.

## Upstream tests

- uWSGI provides global `make check`, `make tests`, and `make unittests`
  targets.
- `make check` runs `cppcheck`; it is not a router_http functional test.
- There is no standalone registered upstream test for the `router_http` plugin
  in the 2.0.31 source tree.
- The official inventory for this package is therefore recorded as 0/0 for
  upstream plugin-specific tests.

## Added test_package

- Builds one C consumer probe.
- The probe validates the packaged plugin is a non-empty ELF shared object and
  contains the uWSGI plugin ABI symbol/name strings:
  `router_http_plugin`, `router_http`, `httpdumb`, and `proxyhttpconnect`.
- The probe intentionally does not require independent `dlopen(..., RTLD_NOW)`
  success because uWSGI plugins are normally loaded by the uWSGI process, whose
  global symbols satisfy plugin references.

## Validation

- W0 dependency gate: `pcre2/10.45` was verified on device
  `10.62.215.229` with a fresh isolated Conan home. Both
  `conan download pcre2/10.45 -r=ohpcd --only-recipe` and
  `conan install --requires=pcre2/10.45 ... --build=never` completed
  successfully for the OHOS/armv8 profile.
- W3 input archive SHA256:
  `27f56cecdcb83ca716ccc51afdb2e012e9e778f3d07653b51775d110066005a5`.
- W3 root:
  `/storage/Users/currentUser/tmp/slot4-uwsgi-router_http-2.0.31-w3-current-20260808051421-35269`.
- `conan create` result: `W3_CONAN_CREATE_RC=0`.
- Build log SHA256:
  `ca0feaad504f58c69edcfc5b2864a65adde351edc969061cfe09317faa94935c`.
- W0 graph log SHA256:
  `d8425367d3fa05293b8b897772c34e5f9fbb8f8c34520e4c1203c87d7499fd31`.
- Package reference:
  `uwsgi-router_http/2.0.31#ad60d1e9868e160a51cdba6dafb75b4c:84fc42d306606bf41517e67fb772179d953edb0a#d405e0c710368746c09f6499fa9b8ad1`.
- Packaged plugin:
  `lib/uwsgi/router_http_plugin.so`, 22848 bytes, SHA256
  `57626de5f73590846d8186d1759ee2f22ac4762f1e2e2d940f55c4ecd88a40a0`.
- ELF check: ELF64 little-endian AArch64 `ET_DYN`; exported
  `router_http_plugin`; dynamic dependency list contains `libc.so`.
- Added test result: `test_uwsgi_router_http` compiled and ran on the device,
  ending with `uwsgi-router_http plugin probe OK: 22848 bytes`.
- Negative test evidence: the same probe returned `1` for a missing plugin path
  (`fopen: No such file or directory`, log SHA256
  `9630fc6e8de277780281f1c6325110913b24059eac34217d6e363abb4982c5d0`)
  and `1` for an empty file (`plugin is too small: 0 bytes`, log SHA256
  `f1fe88e3c0cbe263f11e7206b5d66217cafd474e7f7a78d9a687011602925410`).
