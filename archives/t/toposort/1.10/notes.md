# toposort 1.10 adaptation notes

The fixed PyPI sdist is pure Python, contains one module, and declares no
runtime dependencies. Its SHA-256 is
bfbb479c53d0a696ea7402601f4e693c97b0367837c8898bc6471adfca37a6bd. The
Conan package contains the unchanged toposort.py module and upstream Apache
2.0 license. Its build runs the upstream unittest suite. The Conan 2.29 test
consumer declares run=True, imports from the package folder, checks
toposort.__file__, and exercises the public API.

## Verification

Local CPython 3.11 runs passed the unchanged upstream suite (11/11) and the
consumer script (6 cases). H1-001 used HarmonyOS aarch64, Python 3.12.9, and
Conan 2.29.1. In the single finish run, Conan created package
da39a3ee5e6b4b0d3255bfef95601890afd80709, revision
ed6120c5eb470f7659eeb90c6bdb048c, and verified the packaged module SHA-256
54e9d07cb28d940a22b08ef2de176ad12c7cf90a4a4502e56c70ad83e32c570e. The
upstream suite passed 11/11 and the Conan test_package consumer passed 6/6
cases (8 assertions). The internal W3 setup and build steps both returned 0;
L0, L1, L4, and L5 passed. L2 was skipped because this pure Python package has
no bin/ directory. The exact run evidence archive is
D:/华为鸿蒙/work/toposort-1.10/evidence/h1-001/toposort-11235-h1-evidence.tar.gz
(SHA-256 83fd12d9e44486ba32b24fa6a9ef1b7df148d7fc5e403946e133e0d64d3c5aa4).

The complete finish command returned 1, so the result is built, not a
successful full finish or publication. Conan Verify's G1 static check asks
for export_sources() and patch application; this recipe has no patches because
the fixed upstream source needs none. The old G0 local-tarball check and
Step 10 packaging/ and .staging-verified requirements belong to the
deprecated tar/DESTDIR delivery path; no tarball or marker was fabricated.
Step 5b found missing fields in unrelated existing knowledge entries
E219/E253/E305. Step 8 hit the framework error
'str' object has no attribute 'append'. The result retains these failures;
their classification as legacy or framework conflicts is an internal
disclosure, not an official exemption. A local reports/test-report.md supports
submit readiness but is ignored by repository rules; all material test results
and limits are retained in this tracked notes file and the PR description.

No official PR CI has run. The competition task board labels #11235 lang=cpp
although this is a Python library. Eligibility and points remain unconfirmed;
these notes make no claim that the task qualifies or will earn points.

## 最终状态

`built` — H1 Conan build and W3 passed; full `finish` returned RC 1 as detailed
above. This is not `published`, merged, official-CI-passed, or competition-
accepted status.
