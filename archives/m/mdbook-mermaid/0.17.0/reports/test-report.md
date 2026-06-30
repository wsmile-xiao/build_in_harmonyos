# mdbook-mermaid 0.17.0 Test Report

**Date**: 2026-06-04
**Tester**: AI Compile Agent
**Build System**: cargo (Rust)

## Test Execution

### cargo test --release --ignore-rust-version

**Result**: ✅ PASS

### Unit Tests (src/lib.rs)
- test::crlf_line_endings ... ok
- test::adds_mermaid ... ok
- test::leaves_html_untouched ... ok
- test::html_in_list ... ok
- test::leaves_tables_untouched ... ok
- test::escape_in_mermaid_block ... ok
- test::more_backticks ... ok

**Summary**: 7 passed; 0 failed; 0 ignored

### Integration Tests (tests/it/main.rs)
- install::some ... ok
- install::empty ... ok
- install::full ... ok
- install::missing_js ... ok

**Summary**: 4 passed; 0 failed; 0 ignored

### Binary Tests (src/bin/mdbook-mermaid.rs)
- 0 tests (no tests in binary source)

**Summary**: 0 passed; 0 failed

### Doc Tests
- 0 doc tests

**Summary**: 0 passed; 0 failed

## Overall Result

**Total**: 11 tests, all passed ✅

## Binary Verification

```
$ mdbook-mermaid --version
mdbook-mermaid 0.17.0
```

**File type**: ELF 64-bit LSB executable, ARM aarch64, version 1 (SYSV), statically linked, not stripped
