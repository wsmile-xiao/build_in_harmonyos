cmake_minimum_required(VERSION 3.15)
project(test_signal_tlsd C)

# signal-tlsd 0.1.3 is a pure Rust binary crate; the C test verifies the
# core ALPN Fallback parsing and Rules allowlist logic (the exact logic
# covered by upstream src/alpn.rs #[test] (7) and src/rules.rs #[test]
# (8)) using a standalone C re-implementation. Each upstream #[test]
# case is mapped 1:1 to a C test function with identical assertions.
add_executable(test_signal_tlsd test.c)

enable_testing()
add_test(NAME test_signal_tlsd COMMAND test_signal_tlsd)
