# Almond

Almond is a minimal AMD API implementation for optimized browser bundles. The Conan package installs the platform-independent `almond.js` resource under `share/almond` and publishes that location through `cpp_info.resdirs`.

## OHOS adaptation

No source patch or native compilation is required. The recipe validates the release source, packages the JavaScript loader and metadata, and exposes no native libraries or executables.

## Dependencies

The package has no runtime package dependencies. `quickjs/2024-01-13` is a test-only dependency used to execute the packaged AMD API during `conan create`.

## References

- Homepage and source: https://github.com/requirejs/almond
- Release tag: https://github.com/requirejs/almond/tree/0.3.3
