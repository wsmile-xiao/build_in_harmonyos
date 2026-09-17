# Boost.Filesystem 1.84.0 HarmonyOS adaptation

Boost.Build executes shell probes that are incompatible with the OHOS target.
This recipe compiles Boost.Filesystem's upstream source files directly and
archives them as `libboost_filesystem.a`.

The consumer test creates a directory, writes a file, queries its size and
iterates the directory through Boost.Filesystem APIs.

The upstream test sweep covers 32 targets in the independent validation record:
29 pass and 3 are skipped on OHOS. The skipped targets are
`operations_test`, `operations_test_static`, and `operations_unit_test`.
The first two depend on HMDFS hard-link/symlink creation and POSIX chmod
semantics; the latter requires reading the sandbox root directory `/`.
These are known platform restrictions (E079/E018/E046), not library defects.
The `copy_test` compile path uses
`BOOST_SP_NO_PTHREAD_SETCANCELSTATE`, the Boost-supported fallback for the
pthread cancellation APIs absent from OHOS musl.
