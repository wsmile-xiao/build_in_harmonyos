# bruno-cli

Bruno CLI (bru) — command-line tool for running Bruno API collections.

## Overview

Bruno is an open-source API client for REST, GraphQL, gRPC and Websocket.
The CLI version (`@usebruno/cli`) allows running API collections from the
command line, making it suitable for CI/CD pipelines and automated testing.

## Build System

- **Type**: npm (Node.js package)
- **Source**: npm registry tarball
- **No native compilation required** — pure JavaScript

## OHOS Adaptation

- Uses Node.js runtime supplied by OpenHarmony with `--jitless` flag
- npm dependencies are installed at build time and bundled in the package
- Shell launcher script wraps the Node.js entry point

## License

MIT
