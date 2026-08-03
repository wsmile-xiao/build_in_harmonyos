# httpstat 1.3.2 Adaptation Notes

## Build Environment

- Build system: custom single-file Python package
- Adaptation date: 2026-07-17
- Target: OHOS aarch64
- Status: built

## Packaging Steps

1. Download the official 1.3.2 source archive and verify its SHA256.
2. Apply the Python 3, standard-library fallback, and upstream test endpoint patches.
3. Run `httpstat.py --version` as a source-level sanity check.
4. Install the script as `bin/httpstat` and set executable permissions.
5. Run all 13 upstream scenarios and 15 assertions with Python and Python 3
   (30 assertion executions).
6. Run offline CLI assertions and a loopback HTTP request against the packaged command.

## Adaptation Decisions

| Issue | Cause | Resolution |
|---|---|---|
| Generic `python` shebang | The package requires Python 3 | Rewrite it to `/usr/bin/env python3` |
| Retired Akamai test page is too short for truncation assertions | The upstream endpoint changed after the 1.3.2 release | Replace it with the stable httpbin UTF-8 response without removing a test |
| Upstream tests require public network endpoints | CI network access is not deterministic | Run the complete suite separately and keep `test_package` deterministic |
| HTTP execution depends on curl | The OHOS CI image does not provide a system curl command | Retain curl when present and add a Python standard-library fallback for basic HTTP/HTTPS requests |

## Source Changes

- `0001-use-python3-shebang.patch`: selects Python 3 for direct command execution.
- `0002-add-stdlib-http-fallback.patch`: imports the standard-library fallback modules.
- `0003-use-stdlib-when-curl-is-missing.patch`: uses Python's HTTP stack when curl is absent.
- `0004-refresh-upstream-test-endpoint.patch`: refreshes the HTTPS body fixture used by the unchanged truncation assertions.

## Validation

The complete upstream `httpstat_test.sh` suite passed all 15 assertions with
both Python and Python 3, for 30 successful assertion executions. Clean Linux
`conan create` downloaded and verified the official source, applied the
patches, packaged `bin/httpstat`, and passed all 11 consumer assertions,
including a loopback request with curl removed from PATH. The recipe does not
compile native code; the competition CI worker remains the final platform
verification.

Curl-specific extra options still require a real curl command. The fallback covers
basic HTTP/HTTPS URL requests.
