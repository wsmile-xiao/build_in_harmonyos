# E337 - Task-local Autotools bootstrap closure for OHOS Conan tools

> Contributor: wxjshr | Status: DRAFT | Created: 2026-08-24

## Scope

Use this pattern when an OHOS Conan build must run `autogen.sh` from a source
archive that does not contain a generated `configure` script, while Automake,
Gettext, Libtool, or GLib generator programs come from Conan packages. It is
based on the avahi-glib 0.9_rc5 adaptation and is intentionally limited to
task-owned recipe staging; it does not modify dependency packages or upstream
source files.

## Sequential failure pattern

The bootstrap can expose two independent failures in sequence:

1. Scripts in a cross-UID Conan cache are readable, but direct shebang
   execution fails with `Permission denied`. This affected Automake Perl
   programs, GLib Python generators, and directly invoked shell tools.
2. Invoking the same script explicitly through its interpreter removes the
   execution error, but Gettext or Libtool can still resolve data below a
   build-time prefix such as `//share` or a different Conan home. Representative
   failures include a missing Gettext source directory or missing Libtool
   `build-aux` data.

Fixing only one half is insufficient: a relocatable script that cannot execute
still blocks bootstrap, and an executable bridge around a script with stale
data paths only advances the failure to the next lookup.

## Root cause

Conan tool packages contain programs implemented in shell, Perl, and Python.
On the OHOS worker used for avahi-glib, HMFS policy allowed the current task to
read package-cache scripts but rejected direct execution across the cache UID
boundary. Changing mode bits was not a reliable remedy.

Gettext and Libtool introduced a separate packaging concern. Their installed
scripts retained prefix or data-directory values from package creation. Conan
packages are relocatable, so those values did not necessarily describe the
consumer's package folder. The correct data exists, but the script looks in the
wrong tree.

There is also a caller-semantics exception: Avahi's `autogen.sh` locates
`gettextize`, transforms the program text with `sed`, and pipes it to `sh`.
Putting an ELF launcher at that particular path makes the file executable but
violates the caller's expectation that the command itself is readable shell
text.

## Recommended solution

Build a task-local closure below the recipe build folder:

1. Resolve the Automake, Gettext, Libtool, and GLib package folders from the
   Conan dependency graph. Do not derive them from a hard-coded Conan home.
2. Copy only the required scripts into task-owned staging directories.
3. For Automake Perl tools, compile small native launchers that execute the
   fixed OHOS Perl binary, the packaged real script, and explicit Automake data
   directory arguments.
4. For GLib Python generators, compile native launchers that execute the
   current validated Python interpreter with the staged script.
5. For directly invoked shell tools such as `libtoolize`, use a native launcher
   that executes `/bin/sh` with a staged script.
6. Keep `gettextize` as staged shell text when the upstream bootstrap reads it
   with `sed`; patch only the copied script's prefix.
7. Replace the copied Libtool script's prefix, `datadir`, `pkgauxdir`,
   `pkgltdldir`, and `aclocaldir` with paths below the resolved package folder.
   Clear a conflicting relocation override when the staged script already has
   concrete correct paths.
8. Put staged command directories first in `PATH` and set supported build-tool
   variables to those commands and data directories.

The avahi-glib implementation is in
`archives/a/avahi-glib/0.9_rc5/conanfile.py`, primarily
`_stage_automake_tools()`, `_stage_bootstrap_tools()`, and
`_stage_glib_python_tools()`.

## Verification

The frozen avahi-glib recipe commit `8d7447081cfa` passed a single-package
shadow CI run on an aarch64 OHOS device:

```text
run_root=/storage/Users/currentUser/ohpc-ci-shadow/runs/8d7447081cfa-20260824T100458Z-run-56003
setup_rc=0
build_rc=0
upstream_make_check=1/1 passed
test_package=8/8 passed
build_summary=Total 1, Success 1, Failed 0
```

The result proves that the full `autogen.sh` bootstrap, four-library ordered
build, upstream GLib-loop test, installation, Conan packaging, and consumer
test completed without editing the Automake, Gettext, Libtool, or GLib package
caches.

## Forbidden shortcuts

- Do not `chmod`, patch, or replace files inside a dependency package cache.
- Do not hard-code `/storage/Users/<name>/.conan2/...` paths.
- Do not assume explicit interpreter invocation also fixes embedded data paths.
- Do not replace a tool with a native launcher until checking whether upstream
  executes it or reads its contents as text.
- Do not treat repeated retries as a fix for a deterministic HMFS policy
  failure.

## Relation to existing knowledge

- E209 covers generic `libtoolize`/`ltmain.sh` bootstrap failure.
- E228 covers Automake test wrappers around generated Libtool programs.
- E260 covers a different security boundary for validated native interpreter
  launchers.
- The E324 draft covers a hard-coded `sed` path causing incorrect Libtool
  aux-directory detection.

This draft instead records the combined Conan tool-package execution and
relocation closure required before an Autotools bootstrap can run on OHOS.
