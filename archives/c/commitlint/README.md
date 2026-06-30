# commitlint

## Description
commitlint is a tool to lint Git commit messages according to the Conventional Commits specification. It helps maintain a consistent commit history format, making it easier to generate changelogs and automate versioning.

## Technical Information
- **Language**: TypeScript / JavaScript
- **Runtime**: Node.js
- **Package Manager**: npm / yarn (monorepo with lerna)
- **Version**: 19.8.0
- **License**: MIT
- **Source**: https://github.com/conventional-changelog/commitlint

## Build Notes
- commitlint is a pure JavaScript/TypeScript tool - no platform-specific compilation needed
- The monorepo uses lerna + yarn workspace
- TypeScript build: `tsc -b`
- Installation: `npm install -g @commitlint/cli`
- esbuild (vitepress docs dependency) does not support OpenHarmony; use `--ignore-scripts` to skip native module compilation
- Node.js v24.13.0+ required

## Dependencies
- Node.js >= v18 (tested with v24.13.0)
- npm or yarn
