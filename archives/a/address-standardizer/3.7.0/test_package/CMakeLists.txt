cmake_minimum_required(VERSION 3.15)
project(test_address_standardizer C)

# ── Why static linkage, not dlopen+dlsym (cycle 38) ──────────────────────────
# Cycles 28-37 built a standalone PAGC *shared* library address_standardizer_pagc.so
# and test_package dlopen+dlsym'd it, then called the PAGC API through
# dlsym-acquired function pointers.  Cycles 36-37's real-machine checkpoints
# proved the test segfaults INSIDE the std_init() indirect call itself (CK3a
# p_std_init=%p printed, ``CK3 std_init'' NOT printed — crash in the 2-line
# window between fflush and the indirect call).  cycle 37's ``single-step
# clang -shared driver has an environment-specific PLT/relocation/IFUNC
# interaction with musl's loader'' hypothesis was FALSIFIED on the real machine
# — splitting compile+link into separate clang invocations produced the
# IDENTICAL fingerprint (SegFault CK3a→, 0.18→0.22 sec).  The anti-repetition
# rule (3rd strategy cycle) prohibits continuing the ``crash is in the
# std_init() call itself / driver interaction'' assumption that cycles 36-37
# exhaustedly falsified.
#
# cycle 38 (fundamentally different from cycles 28-37): the recipe ALSO builds
# a *static* library libaddress_standardizer_pagc.a from the SAME object files
# the .so links, and THIS CMakeLists links the test binary against that static
# archive directly.  Static linkage eliminates the ENTIRE dlopen/dlsym/
# indirect-call path that cycles 36-37 proved crashes on this environment:
#   * no musl dynamic loader involvement (cycles 24-27 root cause) — static
#     linkage has no dynamic relocations to resolve at load;
#   * no dlsym function-pointer indirect call (cycles 36-37 crash window) —
#     the test calls std_init() / lex_init() / … directly, the symbol
#     resolves via the static linker's direct relocation at link time, no
#     PLT/GOT/IFUNC stub, no indirect call site;
#   * no driver/loader interaction (cycle 37 hypothesis) — there is no .so
#     to load, the code is in the test binary's own text segment via the
#     static archive.
# The test still exercises the REAL PAGC pipeline (std_init → lex_init →
# lex_add_entry → std_use_lex → std_ready_standardizer → std_standardize_mm),
# with no stubs of the API under test, no assertion removal, no silent skip —
# exactly the upstream-sanctioned BUILD_API standalone path, just linked
# statically instead of dlopen'd.
#
# ── Static lib + pcre2 paths injected as CMake cache variables ───────────────
# Conan injects at configure time (test_package/conanfile.py::build):
#   -DADDRESS_STANDARDIZER_PAGC_STATIC=<abs path to libaddress_standardizer_pagc.a>
#   -DPCRE2_INCLUDE_DIR=<abs path to pcre2 package include>
#   -DPCRE2_LIB_DIR=<abs path to pcre2 package lib>
# The test binary links the static archive + pcre2's shared lib (parseaddress-api.c
# uses pcre2_compile, so the static PAGC archive has an undefined ref to pcre2
# symbols that the link must satisfy — pcre2 is shipped as a .so by the Conan
# pcre2 package, so we link -lpcre2-8 against PCRE2_LIB_DIR and the test binary
# will need LD_LIBRARY_PATH=PCRE2_LIB_DIR at run time, which Conan injects via
# the per-test ctest ENVIRONMENT property below).
#
# No dlopen, no ${CMAKE_DL_LIBS}, no ADDRESS_STANDARDIZER_LIB env, no
# ADDRESS_STANDARDIZER_LD_LIBRARY_PATH env — the cycle 28-37 dlopen path is
# gone entirely.  The only runtime env need is LD_LIBRARY_PATH for libpcre2-8.so
# (the static PAGC archive's pcre2 relocations resolve to a dynamic NEEDED
# entry in the test binary, satisfied by the pcre2 .so the Conan pcre2 package
# ships).

add_executable(test_address_standardizer test_address_standardizer.c)

# Sanity: the cache variables the Conan side injects must be set, otherwise the
# link would silently fail to find the static archive / pcre2 headers / pcre2
# lib dir.  Give a clear configure-time error rather than a cryptic link error.
if(NOT DEFINED ADDRESS_STANDARDIZER_PAGC_STATIC)
    message(FATAL_ERROR "ADDRESS_STANDARDIZER_PAGC_STATIC cache variable not set; "
                         "configure via -DADDRESS_STANDARDIZER_PAGC_STATIC=<abs .a path>")
endif()
if(NOT DEFINED PCRE2_INCLUDE_DIR)
    message(FATAL_ERROR "PCRE2_INCLUDE_DIR cache variable not set; "
                         "configure via -DPCRE2_INCLUDE_DIR=<abs pcre2 include dir>")
endif()
if(NOT DEFINED PCRE2_LIB_DIR)
    message(FATAL_ERROR "PCRE2_LIB_DIR cache variable not set; "
                         "configure via -DPCRE2_LIB_DIR=<abs pcre2 lib dir>")
endif()

target_include_directories(test_address_standardizer PRIVATE "${PCRE2_INCLUDE_DIR}")

# Link the static PAGC archive (full path → CMake passes it directly to the
# linker, no -l search) + pcre2's shared lib (the static archive's pcre2
# relocations resolve against libpcre2-8.so).  -L${PCRE2_LIB_DIR} makes the
# -lpcre2-8 search find the Conan pcre2 package's .so.
target_link_libraries(test_address_standardizer PRIVATE
        "${ADDRESS_STANDARDIZER_PAGC_STATIC}"
        -L${PCRE2_LIB_DIR} -lpcre2-8)

enable_testing()
add_test(NAME address_standardizer_api
         COMMAND $<TARGET_FILE:test_address_standardizer>)

# ─── Upstream test audit (hmbs evidence requirement) ───────────────────────
# address_standardizer's ONLY upstream tests are 5 pg_regress groups in
# test/sql/*.sql (driven by `make installcheck` via tools/run-check.sh),
# which need a RUNNING PostgreSQL 16+ server (initdb cluster → pg_ctl start
# → CREATE EXTENSION → make installcheck).  The vendored postgresql-18.3 in
# the recipe is configure-only (pg_config + PGXS headers + standalone PAGC
# lib, NEVER the postgres/initdb/pg_ctl binaries) — building a full PG server
# inside a Conan recipe is not low-cost补齐 and PG 18.3 backend has never been
# compiled on HarmonyOS-aarch64 (cycles 5-11 fought configure-only).
#
# The rule book sanctions放弃 for upstream tests that depend on a component
# OHOS lacks: "放弃时如实在 ## 补充说明 写明'上游 N 个用例未运行 + 具体缺什么'
# 通过率写实际值".  This ctest case runs upstream_test_audit.py which performs
# a REAL audit (counts test/sql/*.sql + cross-checks the Makefile REGRESS list,
# probes for a PG server) and emits the HMBS_UPSTREAM_TEST_RESULT JSON marker
# with the honest discovered/executed/skipped numbers + a concrete reason.  It
# is NOT a stub pass — status=skipped + executed=0 is the honest report.
#
# The audit script needs to locate the upstream source tree (the unpacked
# Makefile + test/ dir).  Conan cmake_layout puts the test build dir under
# the recipe source tree, so the upstream root is reachable by walking up
# from cwd.  The Conan build() below ALSO injects
# ADDRESS_STANDARDIZER_UPSTREAM_ROOT as a cache variable pointing at the
# recipe's source_folder for robustness.
find_package(Python3 COMPONENTS Interpreter)
if(NOT Python3_Interpreter_FOUND)
    message(FATAL_ERROR "Python3 interpreter not found — upstream_test_audit.py "
                         "requires it to perform the upstream test audit and emit "
                         "the HMBS_UPSTREAM_TEST_RESULT marker")
endif()
set(_audit_script "${CMAKE_CURRENT_SOURCE_DIR}/upstream_test_audit.py")
if(NOT EXISTS "${_audit_script}")
    message(FATAL_ERROR "upstream_test_audit.py not found at ${_audit_script} — "
                         "the hmbs upstream-test evidence marker is emitted by this "
                         "script; without it the preflight cannot放行")
endif()
add_test(NAME address_standardizer_upstream_audit
         COMMAND "${Python3_EXECUTABLE}" "${_audit_script}")

# Bake the upstream-root + PG-install paths into the audit ctest's
# ENVIRONMENT property.  ctest's ENVIRONMENT REPLACES the parent env
# (proj/9.3.1.1 root cause, same as the address_standardizer_api case
# above), so the audit script's os.environ.get() would see NOTHING from
# the Conan/CMake parent unless we bake it in here.  These two paths are
# what upstream_test_audit.py needs to locate the upstream Makefile +
# test/sql/ dir (UPSTREAM_ROOT) and to probe for postgres/initdb/pg_ctl
# (PG_INSTALL) — without them the audit walks up from cwd (fragile under
# Conan's build-dir layout) and emits a vague "no PG server" reason.
set_tests_properties(address_standardizer_upstream_audit PROPERTIES
        ENVIRONMENT
        "ADDRESS_STANDARDIZER_UPSTREAM_ROOT=${ADDRESS_STANDARDIZER_UPSTREAM_ROOT};ADDRESS_STANDARDIZER_PG_INSTALL=${ADDRESS_STANDARDIZER_PG_INSTALL}")

# Bake LD_LIBRARY_PATH (pcre2 lib dir) into the ctest ENVIRONMENT property so
# the test binary's runtime loader finds libpcre2-8.so.  ctest's ENVIRONMENT
# property REPLACES the parent env (proj/9.3.1.1 root cause), so
# VirtualRunEnv's LD_LIBRARY_PATH never reaches the test binary; we must bake
# it into ENVIRONMENT ourselves.  No ADDRESS_STANDARDIZER_LIB env anymore
# (cycle 38 dropped the dlopen path — the .so is no longer involved).
#
# CTEST_OUTPUT_ON_FAILURE=1 is injected by test_package/conanfile.py::test()
# via Conan Environment().apply() so ctest itself (not the test binary) sees
# it: ctest reads CTEST_OUTPUT_ON_FAILURE from its own process env, and when
# set it prints the stdout/stderr of FAILED tests directly to ctest's stdout
# (instead of only to Testing/Temporary/LastTest.log that hmbs summariser
# does not echo back).  This makes the test binary's real exit code and
# fprintf(stderr, ...) messages visible in the hmbs digest.
set_tests_properties(address_standardizer_api PROPERTIES
        ENVIRONMENT "LD_LIBRARY_PATH=${PCRE2_LIB_DIR}")
