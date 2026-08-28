# DRAFT - GNUstep Make environment closure for gnustep-base on OHOS

> Contributor: xuguowei | Status: DRAFT | Created: 2026-08-27

## Scope

Use this pattern when adapting a GNUstep library with Conan on OHOS. The
gnustep-base 1.31.1 recipe showed that GNUstep packages are not plain
Autotools projects: `configure`, `GNUmakefile`, library staging, and downstream
consumers all expect the same GNUstep Make installation domain.

## Symptom

Typical failures appear before or during the first build slice:

```text
GNUSTEP_MAKEFILES is not set
GNUstep Makefiles could not be found
/bin/sh: inaccessible or not found
Permission denied
```

A partial environment can move the failure later. For example, configure may
find GNUstep Make, but the `Source` build or packaging step can still place
headers and libraries outside the GNUstep `SYSTEM` domain expected by consumers.

## Root Cause

GNUstep Make supplies build rules and domain variables that the upstream
GNUmakefiles read repeatedly. Supplying only `CC`, `CFLAGS`, or a conventional
Autotools prefix does not describe where GNUstep headers, libraries, tools, and
configuration files should live. On OHOS, shell script paths also matter because
some upstream and tool-package scripts assume `/bin/sh`.

## Recommended Solution

Build a task-local GNUstep environment from Conan dependency metadata:

1. Resolve the `gnustep-make` build requirement package folder.
2. Prepend its `bin` directory to `PATH`.
3. Set `GNUSTEP_MAKEFILES` to `share/GNUstep/Makefiles` from that package.
4. Set `GNUSTEP_SYSTEM_ROOT` to the current recipe package folder.
5. Set `GNUSTEP_CONFIG_FILE` to a package-local `GNUstep.conf`.
6. Set or pass `GNUSTEP_INSTALLATION_DOMAIN=SYSTEM` for configure and make.
7. Add the current package and dependency library directories to
   `LD_LIBRARY_PATH` for both build and run environments.
8. Rewrite or invoke shell scripts through an OHOS-available shell only in the
   task-owned source/build tree or in copied script staging, never inside a
   shared Conan package cache.

For gnustep-base 1.31.1, this closure was used around configure, the `Source`
GNUmakefile build, package artifact staging, and `package_info()`.

## Verification

The gnustep-base 1.31.1 branch passed single-package shadow CI:

```text
preflight: /storage/Users/currentUser/ohpc-ci-shadow/gnustep-shadow-state/runs/447d960d1462-20260825T192807Z-preflight-4871
heavy:     /storage/Users/currentUser/ohpc-ci-shadow/gnustep-shadow-state/runs/447d960d1462-20260825T192834Z-run-5127
L0: pass
L1: pass, test_package executed
L2: skip, no bin/ dir
L4: pass, no patches
L5: warn, no artifacts found
```

The consumer test linked and executed a Foundation program using the packaged
GNUstep layout.

## Forbidden Shortcuts

- Do not treat GNUstep libraries as prefix-only Autotools packages.
- Do not run configure with `GNUSTEP_MAKEFILES` and then omit the same domain
  variables from make or the run environment.
- Do not hard-code a developer-specific Conan cache path.
- Do not patch or chmod files inside the `gnustep-make` package cache.
- Do not call a C-only smoke test sufficient for a GNUstep Foundation package.
