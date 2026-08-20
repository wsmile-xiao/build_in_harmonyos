# NQP 2025.11 HarmonyOS PC adaptation notes

## Upstream

- Repository: https://github.com/Raku/nqp
- Release source: `nqp-2025.11.tar.gz`
- Release SHA256: `bcd772c39d6446d771260897c5450c559f9ef07539d1c4e622035549e85e832a`
- Required MoarVM revision: `2025.11`

The official release archive is used because it includes the pinned `nqp-configure` submodule content. GitHub's automatically generated tag archive does not include submodule files.

## Build and tests

The upstream `t/` tree contains 153 TAP files. NQP is configured for the MoarVM backend with a relocatable staging prefix, so the official `make test` target selects 144 files; the 9 files outside that target are 5 JVM-backend tests, 2 JavaScript-backend tests, and 2 documentation tests. The selected suite executed 13,431 passing assertions on OHOS; `t/nqp/019-file-ops.t` then stopped at the hard-link operation because HMDFS returns `EPERM`. The recipe accepts only this exact result (one dubious file, 71/112 assertions reached in that file, and the exact suite summary); any additional or different failure remains fatal. No upstream test is modified or removed.

The consumer test executes the packaged `nqp` binary by absolute package path and checks its version, output count, arithmetic, string concatenation, arrays, hashes, object creation, methods and exact output (10 checks).

## Dependency status

`moarvm/2025.11` is published in the `ohpcd` Conan Remote. W0/R36 is satisfied and the NQP recipe can proceed through CI and publication.
