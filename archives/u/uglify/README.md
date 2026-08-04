# uglify

uglify packages UglifyJS (`uglify-js` on npm), a JavaScript parser,
mangler/compressor, minifier, and beautifier toolkit.

## Features

- Parses and transforms JavaScript
- Compresses and mangles JavaScript for smaller production assets
- Beautifies generated output when requested
- Provides the `uglifyjs` command-line tool

## OpenHarmony Adaptation

UglifyJS 3.19.3 is portable JavaScript and requires no native compilation.
The package installs the upstream runtime files under `res/uglify-js` and
provides a shell launcher in `bin/uglifyjs`. The launcher invokes the Node.js
runtime supplied by the OpenHarmony environment with `--jitless`, matching the
validated execution mode for Node.js on HarmonyOS aarch64.

The official upstream Git tag archive is used instead of the smaller npm
distribution tarball so the complete upstream test suite remains available
during `conan create`.

## Dependencies

- Runtime: OpenHarmony-provided Node.js with `--jitless` support
- Upstream engine declaration: Node.js 0.8 or newer
- Conan runtime dependencies: none
- Upstream-test-only npm dev dependencies: `acorn` and `semver`

## References

- Homepage and source: https://github.com/mishoo/UglifyJS
- npm package: https://www.npmjs.com/package/uglify-js
- License: BSD-2-Clause
