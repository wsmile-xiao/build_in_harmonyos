# dhcpoptinj 0.5.3 HarmonyOS PC adaptation notes

## 1. Upstream
- Repo: https://github.com/misje/dhcpoptinj, tag 0.5.3 (2019-08-07).
- Tarball: https://github.com/misje/dhcpoptinj/archive/refs/tags/0.5.3.tar.gz (34547 bytes).
- SHA256 c7517f1c75d6890e7dd42bbd24b870f500803ae3b145d31940e60baee5eba298 (matches Debian orig tarball).
- Build: CMake (add_executable only), C99, links libnetfilter_queue.
- License: GPL-3.0-only.

## 2. Tests audit (upstream has zero tests)
- Root: no tests/ or test/ directory (only src/, CMakeLists.txt, README.md, CHANGELOG.md).
- CMakeLists.txt: no enable_testing()/add_test(); only find_library(NFQ_LIB) + install sbin.
- .travis.yml: only cmake .. + make -j2, no test step.
- src/*.c scan: no TEST/TEST_F/cmocka/munit harness; hits are ordinary English words.
- Conclusion: upstream_tests_exist=false; test_package validates packaged binary instead.

## 3. Dependencies (all inline; no external requires)
- libnfnetlink 1.0.2: vendored inline from https://www.netfilter.org/projects/libnfnetlink/files/libnfnetlink-1.0.2.tar.bz2 (sha256 b064c7c3d426efb4786e60a8e6859b82ee2f2c5e49ffeea640cfe4fe33cbc376, same as archives/l/libnfnetlink/1.0.2). Rationale (2026-09-11 preflight): conan resolved libnfnetlink/1.0.2 from conancenter whose validate() rejects os=OHOS ("only supported on Linux"), failing the graph before build. Vendoring sidesteps remote-order shadowing; -include compat_fixup.h covers the OHOS sockaddr_storage fix so no extra patches needed.
- libmnl 1.0.5: NOT in registry -> inline build from https://www.netfilter.org/projects/libmnl/files/libmnl-1.0.5.tar.bz2 (sha256 274b9b919ef3152bfb3da3a13c950dd60d6e2bcd54230ffeca298d03b40d0525).
- libnetfilter_queue 1.0.5: NOT in registry -> inline build from https://www.netfilter.org/projects/libnetfilter_queue/files/libnetfilter_queue-1.0.5.tar.bz2 (sha256 f9ff3c11305d6e03d81405957bdc11aea18e0d315c3e3f48da53a24ba251b9f5).
- Precedent: archives/f/fprobe-ulog/1.2 (inline libmnl + libnetfilter_log, requires libnfnetlink).

## 4. OHOS fixes
- CMAKE_PREFIX_PATH points to inline prefixes + libnfnetlink package so find_library(NFQ_LIB) resolves without patching upstream CMakeLists.
- Autotools inline deps: stub config.guess/config.sub (aarch64-unknown-linux-gnu), umask 077->022 for HMDFS, compat_fixup.h for OHOS socket header (_UAPI_LINUX_SOCKET_H + __kernel_sa_family_t).
- No __OHOS__ macros added to patches/ (none needed); no R49 SYS_PREFIX pollution (build-folder prefixes only).
- R32 validate allows Linux/OHOS; settings include os/compiler/build_type/arch.

## 5. test_package (R34)
- test.c runs real sbin/dhcpoptinj binary: --help usage check, --version 0.5.3 check, invalid-queue negative path (guards against silent-pass harness).
- Emits HMBS_TEST_PACKAGE_RESULT (discovered 3) and HMBS_UPSTREAM_TEST_RESULT status no_tests with audit reason.
- MANIFEST.yml declares upstream_tests_exist:false with 5-point audit.

## 6. Risks
- Runtime needs kernel NFQUEUE + CAP_NET_ADMIN; on HarmonyOS PC the binary builds and --help/--version work, but live packet mangling requires netfilter queue support + privileges. Documented in PR supplement.
- Internal infra (real-device IP, hmbs API, preflight internals) is intentionally omitted from PR body per policy.

## 7. Download reliability (2026-09-11 preflight: Signal 9 + gzip unexpected EOF)
- conandata sources.url is a list: gh-proxy.com mirror first, official GitHub URL last (same mapping as ci/conan/build_and_test.sh); sha256 unchanged.
- Rationale: recipe downloads exactly one gzip archive (main 0.5.3 tarball; inline deps are .tar.bz2), so the gzip truncation error points at the GitHub fetch on the slow direct route; Conan tries list entries in order.
- netfilter.org entries left as single URLs: CI maintains no mirror mapping for that domain, no invented mirrors.

## 8. pkg-config fix (2026-09-11 preflight: LIBMNL...no / pkg-config not found)
- libnetfilter_queue-1.0.5 configure uses PKG_CHECK_MODULES for LIBMNL+LIBNFNETLINK; worker has no pkg-config in PATH so configure aborts even though PKG_CONFIG_PATH was set.
- Fix: build_requirements() tool_requires pkgconf/3.0.5 (precedent burp2/2.1.0), generate() adds VirtualBuildEnv, _build_autotools_dep runs with env=conanbuild; nfq_extra adds explicit LIBMNL_CFLAGS/LIBS alongside LIBNFNETLINK_* as fallback.

## 9. nfnetlink header conflict (2026-09-11 preflight: 10 redefinition errors in nlmsg.lo)
- libnetfilter_queue-1.0.5/src/nlmsg.lo fails: staged libnfnetlink/linux_nfnetlink.h redefines nfnetlink_groups / NFNLGRP_NONE..__NFNLGRP_MAX / nfgenmsg already defined in OHOS sysroot linux/netfilter/nfnetlink.h.
- Fix: nfnl_wrapper (precedent fprobe-ulog/1.2 _create_nfnl_wrapper): build/nfnl_wrapper/libnfnetlink/linux_nfnetlink.h forwards to <linux/netfilter/nfnetlink.h> + <libnfnetlink/linux_nfnetlink_compat.h>, with -I wrapper before staged include for libnetfilter_queue and final cmake; LIBNFNETLINK_CFLAGS likewise prefixed.
