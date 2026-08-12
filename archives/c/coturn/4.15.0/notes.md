# Coturn 4.15.0

The recipe keeps upstream testing disabled by default. On a runnable target,
set `with_upstream_tests=True` to configure `BUILD_TESTING=ON` and run
`ctest --output-on-failure` during `conan create`. Cross builds do not execute
the suite and require separate target-side evidence. Optional database-driver
tests remain controlled by upstream CMake feature discovery and are not
disabled by this recipe.

The packaged `turnutils_rfc5769check` consumer smoke test remains part of
`test_package`; it runs only when the package target is runnable. To obtain
actual HarmonyOS PC evidence, run a native target build rather than treating a
host or cross-build result as target execution:

```sh
conan create archives/c/coturn/4.15.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  -o coturn/*:with_upstream_tests=True \
  --build=missing \
  --build=coturn/*
```

Historical local WSL/Linux validation (GCC 15.2.0) configured the selected
TCP/UDP TURN/STUN scope with `WITH_TLS=OFF` and `WITH_PROMETHEUS=OFF`.
The full configured upstream CTest suite passed `12/12`, including
`test_sqlite_dbd`, and the installed `turnutils_rfc5769check` consumer smoke
passed `1/1`. The complete result is captured in
`build_in_harmonyos/pipeline_logs/coturn-pr3691-local-offline-validation-v5.log`.
This is local host evidence only: the official-source download retried and
timed out in a fresh `conan create`, so the final run used the existing cached
official source plus the same Conan dependency generator. It does not claim
OpenHarmony-target execution or a passing remote CI pipeline.

CI `#12744` reached `conan-build-test` but failed while compiling
`ns_ioalib_engine_impl.c`: the target libevent package has no
`event2/bufferevent_ssl.h`. `WITH_TLS=OFF` had not explicitly applied
`TURN_NO_TLS`/`TURN_NO_DTLS` to the `turnserver` executable, which compiles
that source itself. Patch `0003-cmake-propagate-no-tls-to-turnserver.patch`
now applies those definitions directly to that target. After the patch, a
WSL reconfigure of the cached official source showed both definitions in
`turnserver`'s compile flags; its upstream CTest suite passed `12/12` and the
RFC 5769 consumer smoke passed `1/1`. A fresh OpenHarmony CI run is still
required; this verification is not an OHOS result.
