# socket99 0.2.2 Path B candidate evidence

## Application scope

- Software: `socket99/0.2.2`
- Branch: `feat/socket99-0.2.2`
- Current commit: `f997df87efd2f628a6bb6e0344bb3f6340a700f2`
- Application path: Path A (base adaptation) + Path B (knowledge extension)
- Candidate draft: `knowledge/drafts/E341-draft-BBEA.{kv,md}`
- Associated Issue: `https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/2561`
- Path B result: subject to official reviewer approval

The Path B claim is based on a reusable evidence and accounting pattern, not on
patch size or the number of repair rounds. It combines two independently
verified OHOS worker boundaries while keeping the supported upstream coverage
and installed-package consumer validation visible.

## Reusable problem

The upstream project is a small C99 Makefile library. Its `test_all` harness
launches TCP blocking, TCP nonblocking, UDP, Unix-domain stream, and Unix-domain
datagram client/server pairs. On the target OHOS PC, the library and the TCP/UDP
cases compile and run, but pathname Unix-domain `bind()` returns
`Operation not permitted`. A direct rerun of the same test program below a
user-writable directory produced the same errno, so this is not merely a Conan
cache or one source path problem.

The upstream Makefile's `install` target separately assumes the GNU `install`
utility. The device does not provide that command, so an otherwise successful
build can fail during Conan `package()` with exit 127.

The reusable adaptation is to:

1. prove the capability failure in a writable task-private directory;
2. gate only the affected upstream test group with an explicit environment
   variable and preserve supported groups unchanged;
3. record declared, executed, passed, and skipped counts separately; and
4. use Conan's `mkdir()`/`copy()` for the exact package outputs when the device
   lacks `install`, followed by a real installed-package consumer.

## Same-source before/after evidence

The comparison uses the official source archive SHA-256
`657907afc1e2dc42406d257cc032e97f66739c8d8873c424b567a913d3ffc36e`, the same
OHOS arm64 Conan profile, and the same device toolchain.

| Evidence | Before | After |
|---|---|---|
| Runner input | `conan create` from commit `386f2cdeb7bd5db018a5ba644d6e36079e7b5654` | `conan create` from commit `f997df87efd2f628a6bb6e0344bb3f6340a700f2` |
| Upstream test | TCP/UDP 6 roles passed; Unix stream/datagram 4 roles failed in the same groups after server `bind()` returned `Operation not permitted` | TCP/UDP 6 roles passed; 4 Unix roles explicitly skipped by `SOCKET99_SKIP_UNIX=1` |
| Independent path check | Same Unix `bind()` failure in `$HOME/tmp/socket99-0.2.2-upstream-r1` | No unsupported Unix group is launched on OHOS; supported groups remain unchanged |
| Package stage | `make install` failed: `install: No such file or directory`, Error 127 | Conan `mkdir()`/`copy()` packaged one archive and one public header |
| Consumer | Not reached | `test_package` compiled and ran; 8/8 checks passed |

The first after attempt with the test gate still exposed the missing `install`
utility. That failure was then repaired independently; the final round reached
and passed package creation and consumer execution.

## Adaptation root-cause chain

| Stage | Root cause | Scoped resolution |
|---|---|---|
| public header compile | `socket99.h` used `size_t` and `FILE` without owning standard includes | portable `0001-socket99.h.patch` adds `<stddef.h>` and `<stdio.h>` |
| supported build | OHOS profile needs explicit compiler and archive tools | recipe derives `CC`, `AR`, and `RANLIB` from Conan compiler configuration with fallbacks |
| upstream test | pathname Unix socket `bind()` is denied on this OHOS runner | `0002-test_all.patch` adds `SOCKET99_SKIP_UNIX=1` around only the Unix group; recipe sets it only for `os=OHOS` |
| package stage | GNU `install` is absent on the device | `package()` uses Conan `mkdir()` and `copy()` for `libsocket99.a` and `socket99.h` |
| consumer | upstream harness does not validate Conan's installed layout | one C consumer compiles against the packaged include/lib directories and exercises eight API/configuration checks |

## Duplicate boundary

- E024 covers the general OHOS Unix-domain socket restriction.
- E340 covers a broader AF_UNIX filesystem capability matrix and an abstract
  namespace alternative.
- E098 and E174 cover the missing `install` command and manual installation.
- E341 is deliberately narrower than those single-point entries: it records
  the combined recipe workflow for a minimal Make project—capability probe,
  narrow source-level test gate, honest role accounting, Conan-native package
  materialization, and consumer closure.

The draft does not claim that all AF_UNIX forms are unavailable, does not claim
the skipped roles passed, and does not propose installing tools or relaxing
system permissions on the worker.

## Final validation

- Remote worktree: `$HOME/ws/wt-socket99-0.2.2`
- Remote HEAD: `f997df87efd2f628a6bb6e0344bb3f6340a700f2`
- Runner log: `$HOME/tmp/socket99-0.2.2-w3-r8-count-fix/conan-create.log`
- Runner result: `conan create --build="socket99/*"` returned `0`
- Upstream scope: 5 scenario groups / 10 roles; 6 roles passed and 4 roles
  skipped on OHOS with the recorded reason
- Consumer scope: 1 executable / 8 assertions; 8 passed, 0 failed
- Package: static `libsocket99.a` plus `socket99.h`
- CI and AI Review: to be recorded after PR creation for the same final SHA

## Honest boundary

The device evidence establishes the supported TCP/UDP behavior, the explicit
OHOS test capability boundary, package materialization, and the installed C
consumer. It does not establish pathname Unix-domain socket behavior on every
OHOS release or prove that abstract sockets are available on every worker.
Path B classification and the final knowledge identifier remain subject to
official review.

## Change boundary

This task changes only `archives/s/socket99/0.2.2/` and the directly related
`knowledge/drafts/E341-draft-BBEA.{kv,md}` files. It does not modify dependency
recipes, repository infrastructure, formal knowledge entries, or another
task's files.
