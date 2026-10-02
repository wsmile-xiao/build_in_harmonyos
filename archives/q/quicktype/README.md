# quicktype

quicktype — generate types and converters from JSON, JSON Schema, TypeScript and GraphQL.

## Overview

`quicktype` turns sample data into strongly-typed models and serializers for
C (cJSON), C++, Crystal, C#, Dart, Elixir, Elm, Flow, Go, Haskell, Java,
JavaScript, JavaScript PropTypes, JSON Schema, Kotlin, Objective-C, PHP, Pike,
Python, Ruby, Rust, Scala3, Smithy, Swift, TypeScript, TypeScript Effect Schema
and TypeScript Zod. Upstream: <https://github.com/glideapps/quicktype>.

## Build System

- **Type**: npm (Node.js package), distributed as a pre-compiled CLI
- **Source**: npm registry tarball (`registry.npmjs.org/quicktype/-/quicktype-26.0.0.tgz`)
- **No native compilation required** — the tarball ships compiled JavaScript (`dist/`)

## OHOS Adaptation

- Uses the OpenHarmony Node.js runtime through a shell launcher running `node --jitless`
  (native JIT is not available on OHOS PC)
- The 16 runtime npm dependencies are installed at build time and bundled in the package
- Launcher resolves its own directory, so the package is relocatable

## License

Apache-2.0
