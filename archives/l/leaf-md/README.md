# leaf-md

A friendly terminal Markdown previewer with syntax highlighting, table
formatting and Mermaid diagram support.

## Description

leaf renders Markdown for the terminal. It ships as a TUI previewer as well as
a headless renderer (`--inline`), which makes it usable from scripts and from
integrations that need Markdown rendered to stdout.

The upstream project is `RivoLink/leaf`; the executable it installs is named
`leaf`. This repository packages it as **leaf-md** (the distribution name also
used by the Homebrew formula, since renamed to `leaf-markdown-viewer`).

## Homepage
https://github.com/RivoLink/leaf

## License
MIT

## Build System
cargo (Rust)

## Notes

* Pure cargo build; no system C library is required. The bundled C sources of
  the `onig_sys` (oniguruma) and `ring` crates are compiled by `cc-rs` with the
  OHOS clang driver.
* The produced ELF is signed with `binary-sign-tool`, which HarmonyOS requires
  before it will execute a shipped binary.
* Commands installed: `leaf` (see `commands.json`).

See `1.26.1/notes.md` for the adaptation log and
`1.26.1/reports/test-report.md` for the verification results.
