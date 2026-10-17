# uglifycss

uglifycss is a Node.js command-line CSS minifier derived from the CSS portion
of YUI Compressor. It removes comments and redundant whitespace while
preserving CSS semantics.

## Features

- Minifies CSS from standard input or one or more files
- Writes output to standard output or a file selected with `--output`
- Supports URL conversion and CSS variable expansion options

## OpenHarmony Adaptation

The package contains portable JavaScript and does not build native code. The
installed command is a shell wrapper that invokes the Node.js runtime supplied
by the OpenHarmony build environment with `--jitless`. This is required on the
validated HarmonyOS aarch64 runtime, where default V8 JIT initialization
terminates before JavaScript can run.

## Dependencies

- Build and runtime: Node.js 6.4 or newer
- Conan dependencies: none

## References

- Homepage: https://github.com/fmarcia/uglifycss
- npm package: https://www.npmjs.com/package/uglifycss
- License: MIT
