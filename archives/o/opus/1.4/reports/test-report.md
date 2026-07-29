# Opus 1.4 test report

| Scope | Independent total | Target passed | Status |
|---|---:|---:|---|
| Upstream component executables | 9 | 9 | pass |
| Upstream integration executables | 5 | 5 | pass |
| Installed-package integration | 1 | 1 | pass |

Executable paths, not repeated Meson labels or shared/static reruns, define the
independent upstream inventory.

Fresh target W3 r10 passed both shared and static Conan creates. Each variant ran
all fourteen distinct upstream executable paths and exactly one installed-package
encode/decode consumer. The runner recorded `shared_exit=0`, `static_exit=0`,
and `runner_exit=0`.

Evidence:

- Archive: `E:/HarmonyPC/validation/opus-1.4/device-r10-evidence.tar.gz`
- Archive SHA-256: `fabaa324089dbf56fcd772dfaf67e5c5c7d8bd047ea7545cfcfeba11af777c36`
- Candidate manifest SHA-256: `16844f7561aaa8ba04ed76f08036d8f6dacb468c62e41ac281d9efd7b111a02a`
- Evidence closure manifest SHA-256: `4ccfee475654a0136946e68b3d73f247c9eb3250747c1fffc9ae1df2dd4695a1`
- Shared log SHA-256: `7bedc44db8b5b905b54146cd7534ada9f95c756d555b5fcdbfaf5975c6b4023d`
- Static log SHA-256: `ef13504fa18ab496f291fc8eba3adbefd4769ae7281f6757e42e0da0f4d17193`
- Patch-equivalent r9 candidate manifest SHA-256: `f72ec9812f258fae032beb56979a2c5d50a86894f511df0f7564e41c6d4125d1`
- Patch equivalence: r8 3-patch and r9 9-patch series produce the same 401-file source tree
