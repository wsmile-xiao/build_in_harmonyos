# almond 0.3.3 adaptation notes

## Build environment

- Build system: custom resource packaging
- Build date: 2026-08-20
- Status: built

## Adaptation

Almond 0.3.3 is a platform-independent JavaScript AMD loader. It has no native
compile step and requires no source patch. The Conan recipe validates the AMD API
markers in `almond.js`, packages the script and metadata under `share/almond`, and
publishes that directory through `cpp_info.resdirs`.

## Dependencies

No runtime package dependencies are required. The consumer test uses the published
`quickjs/2024-01-13` package to execute the packaged JavaScript AMD API.

## Verification

The official tag registers 34 browser tests in `tests/all.js`. Upstream runs them
with a Node.js HTTP server and PhantomJS. On this OHOS environment Node.js aborts
with SIGTRAP before script execution, and PhantomJS is neither installed nor
published in the ohpcd remote, so the original browser runner remains unavailable.

To avoid leaving the upstream behavior untested, `test_almond.py` ports every one of
the 34 named scenarios from `tests/all.js` to isolated QuickJS probes. The mapping
preserves each scenario's core Almond assertion (module definition, map config,
plugins, relative IDs, circular dependencies, special dependencies, errors, and
reserved property names). The OHOS run reports each scenario separately and passes
34/34. This is an executable runtime port, not a claim that the original DOH/DOM
harness ran; browser-only harness behavior remains outside QuickJS coverage.

## Source changes

None.
---

**编译结束**: 2026-08-20 03:59
**最终状态**: built
