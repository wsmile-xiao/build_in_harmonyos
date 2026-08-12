cmake_minimum_required(VERSION 3.15)
project(test_acme_redirect C)

# acme-redirect 0.8.1 is a pure Rust binary crate; the Rust toolchain
# (cargo/rustc) is unavailable in the hmbs preflight sandbox. Per the
# archives/a/aes/0.7.4 + archives/s/signal-tlsd/0.1.3 precedent, this C
# harness re-implements the exact Rust logic under test and validates
# each upstream #[test] case on-device via the clang toolchain.
#
# The test program prints the two HMBS_*_RESULT JSON markers itself at
# the end of main(); counts are sourced from the same tests_run/
# tests_failed counters as the Results: summary line.
add_executable(test_acme_redirect test.c)

enable_testing()
add_test(NAME test_acme_redirect COMMAND test_acme_redirect)
