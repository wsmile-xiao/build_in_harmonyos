# iSelect 1.4.2 adaptation notes

The upstream release contains `configure.ac` and `Makefile.in` but no generated
`configure` script. The Conan recipe avoids an Autoconf build requirement by
generating the small configured files in Python and compiling the same upstream
objects directly.

The package links against `ncurses/6.6` and installs the `iselect` CLI plus its
manual page. Upstream does not provide an automated test target; the consumer
test runs the packaged binary with `-V` and `-h` and checks the expected version
and usage output.

Some target C libraries do not declare or provide `reallocarray`, while the
upstream 1.4.2 sources use it from both C and C++ translation units. The recipe
link-checks for `reallocarray` and defines `ISELECT_NEED_REALLOCARRAY` only when
it is missing; `0002-ohos-reallocarray-fallback.patch` then provides a shared
overflow-checked fallback without platform-specific conditionals.

OHOS new-port validation on 2026-08-09:

- Port: `33332`
- Runner task: `iselect-1.4.2-botfix-20260809-r1`
- Run directory: `/storage/Users/currentUser/ohos-test-runs/codex-a-iselect-iselect-1.4.2-botfix-20260809-r1-20260809-015706-36999`
- Result: `ci/conan/build_and_test.sh archives/i/iselect/1.4.2` passed with L0/L1/L2/L4/L5 pass. The `reallocarray` probe failed on OHOS as expected, so the recipe added `-DISELECT_NEED_REALLOCARRAY` and used the shared fallback.
- Full package reference: `iselect/1.4.2#5f07fbdf63a2968d482fa99a543eff2c:5451db01063ffef70a6f03c02395d1808faeb5e5#bf0ee60b4b0477ae88af84d599bf48a1`
- Upstream tests: N/A (`0/0`), because the release source has no automated test target.
- Added consumer validation: `test_package` ran `iselect -V` and `iselect -h` and checked the expected output.
