# Local validation report

- Package: `seatd/0.9.3`
- Date: `2026-08-14`
- Host: Windows, without an OHOS compiler during the front-end phase
- Result: **front-end checks passed; later shadow CI passed on device**

## Passed checks

1. Official SourceHut tag `0.9.3` resolves to
   `daa8196e10b180b8b0caeafa8e5f860eb1bd6706`.
2. The official GitHub mirror archive is 42086 bytes and hashes to
   `302564d54d8e28191fadfd734f2675ecb0c9e0615a58011b89ef15dfa4dbaa96`.
3. Both Conan Python files pass Python 3.12 syntax compilation without creating bytecode.
4. Conan 2.29.1 `inspect` parsed the initial recipes. The final Meson consumer recipe was
   additionally parsed and executed by `conan create` during shadow CI.
5. Conan `graph info` with `ci/conan/profiles/ohos-aarch64` succeeds and contains one node only
   (`seatd/0.9.3`), with no package dependencies.
6. Conan `install --build=never` generates the OHOS Meson native file. It contains one
   `default_library=static` entry and the expected server, backend, documentation, examples, and
   `werror` options.
7. YAML parsing succeeds; SHA256 has 64 lowercase hexadecimal characters;
   `assertion_count: 15` matches 15 unconditional `CHECK(...)` calls.
8. No forbidden `${CC}`, `${CXX}`, `${CFLAGS}`, or `${LDFLAGS}` use appears in the recipe.
9. Path audit is restricted to `archives/s/seatd/0.9.3/`.

## Local limitations

- `conan create`, upstream Meson tests, the consumer executable, L0-L5, and artifact inspection
  could not run on the Windows host. They later passed on HarmonyOS aarch64; see
  `shadow-ci-2146.md`.
- Conan's own HTTP downloader timed out against GitHub on this Windows host. The same archive was
  successfully downloaded with `curl` and hashed, so this was a host-network limitation rather
  than a checksum error. The device CI downloader later fetched and verified the source.
- `poller` remains excluded from the default run based on existing OHOS timeout evidence; it must
  be retried separately with an external timeout.

## Reproduction command

```sh
CI_PACKAGES="archives/s/seatd/0.9.3" zsh ci/conan/build_and_test.sh
```
