# AtomCode current-HEAD assessment

Reviewed HEAD: d98cfcd3b8019cee8f75101343771d0064a6d9e1. The original report is retained without hiding incorrect findings. This is static review, not platform CI or submission.

- D1 shared option is a genuine recipe-contract defect. The local successor declares `package_type = "shared-library"` and removes unsupported shared/fPIC selectors. It does not promise a static Conan variant. The report's claim that upstream lacks PIC is incorrect: upstream top-level CMake sets `-fPIC` in both Debug and Release flags.
- D2 stale run descriptors are genuine. The successor descriptors bind onion-20261005-r020 and reports/r020-validation-binding.json. Historical native and formal evidence is retained separately. Formal r013 is validating the changed recipe; r012 is not reused as proof of the new recipe.
- D3 is a disclosure boundary, not a reproduced layout defect. The HTTP fixture consumes installed `onion/types_internal.h` and `onion/listen_point.h`, and writes the `onion_listen_point.listenfd` and `.listen` fields. It validates the exact pinned v0.8 installed headers and shared-library ABI together. It is not a public-API-only consumer and does not establish ABI compatibility for upgrades. A new upstream version must revalidate this coupling.
- D4 is a false positive. Official tests/ctest.h expands INIT_LOCAL to CHECK_IF_TEST first; for --list that macro prints the function name and returns before any curl setup or network assertion. END exits with accumulated failures, which remain zero in discovery. No test is deleted or weakened.

Native successor r020 completed 89/89 upstream cases, consumer 1/1, independent Harmony-specific test 1/1, full receipt validation, release/postrelease and zero owned processes. This does not replace actual formal-package validation or current-HEAD platform CI.

Formal r013 has now completed actual Conan create and local CI with 89/89 upstream cases and both installed consumers. Snapshot SHA-256: 895aae723e93b5d3a5d38d6a2fb693bc50579e5b4116ad18d607c3cf34ec8669. Aggregate finish RC remains 1 (PARTIAL_POST_W3), with original limitations retained. Platform CI and submission are still separate gates.
