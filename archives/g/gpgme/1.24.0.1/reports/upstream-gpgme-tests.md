# GPGME 1.24.0 upstream test execution report

- Package: `gpgme/1.24.0.1`
- PR: #7424
- Upstream inventory: 51 tests in the enabled adaptation matrix (31 C/OpenPGP, 20 Qt6)
- Qt5 binding/tests are outside the enabled matrix; `t-wkspublish6` is disabled upstream and is not registered.

## C/OpenPGP tests

The C/OpenPGP inventory contains 31 executable tests: the three top-level C tests and the registered OpenPGP sub-suite. The executed result is 30 passed and one compatibility failure.

The stable failure is `t-edit-sign`: GnuPG 2.4 reports fewer UID signatures than the older upstream expectation. This is a runtime/test expectation difference and does not indicate a missing GPGME API.

## Qt6 tests not executed

The 20 registered Qt6 tests (`initial.test`, `final.test`, and the 18 registered Qt6 targets) require the complete Qt test harness, prepared test keyring, `gpg-agent`, and pinentry. The WKD lookup test additionally requires WKD/network key services and dirmngr. These runtime capabilities are outside the current test setup and are not counted as passed.

## Result

- Upstream tests passed: 30/51 (58.82%)
- Upstream tests failed: 1/51 (the `t-edit-sign` compatibility difference)
- Upstream tests not executed: 20/51
- Non-passing upstream items: 21/51
- Added consumer test: 1/1 (100%)
