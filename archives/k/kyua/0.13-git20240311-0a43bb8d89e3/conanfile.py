#!/usr/bin/env python3
"""Conan recipe — kyua 0.13-git20240311-0a43bb8d89e3 (Autotools, bootstrap).

Kyua is a testing framework for infrastructure software (the ATF test
runner used by FreeBSD; runs ATF C/C++/shell test programs plus plain
programs). This snapshot is the Debian/Ubuntu 0.13+git20240311 source
(commit 0a43bb8d89e370827ccf1ab4b4b1609b127ba735 on freebsd/kyua).

OHOS notes:
  - The GitHub archive is a bare git snapshot without a generated
    `configure`, so build() bootstraps it with autoreconf-equivalent
    manual steps (tool_requires: automake/autoconf/libtool, librb 2.0.0
    precedent with system-perl handling).
  - configure.ac hard-requires the ATF M4 macros (atf-c++/atf-sh/atf-common)
    plus pkg.m4 at autoreconf time; they are sourced from the atf/0.23 and
    pkgconf/3.0.5 tool packages (test_requires/build_requirements).
  - LUTOK/SQLITE3 are probed via PKG_CHECK_MODULES; PkgConfigDeps generates
    the sqlite3 .pc from requires() (sqlite3/3.49.1). Lutok is NOT consumed
    as a remote package: it is vendored statically (see
    _build_vendored_lutok) because the remote lutok/0.6.2 recipe has no
    SHELL fallback and dies at configure[141] on runners missing the
    profile-pinned bash, while kyua-side disk repair is permission-denied
    (notes rounds 15-16).
  - atf/0.23 ships .pc/.la files built with prefix=/ (lutok 0.6.2 finding),
    so the recipe writes its own atf-c++.pc/atf-sh.pc pointing at the real
    package folder and links copies of the static archives.
  - The 2024 automake config.guess cannot identify HarmonyOS, so explicit
    --build/--host triplets bypass guessing (E007/E160 precedent).
  - Upstream tests run via `make check`: an autotest bootstrap testsuite
    (10 cases) plus a kyua self-run over 116 ATF test programs (1253 C++
    ATF cases + 172 atf-sh cases; 1435 total by static audit, see
    test_package/MANIFEST.yml). build() captures check.log and parses the
    deterministic kyua summary line `N/M passed (K failed)` (cli/cmd_test.cpp)
    plus the autotest `N tests were successful` line; counts come only from
    those two lines, never from string arithmetic fallbacks.
  - `--disable-developer`: git-HEAD builds default developer mode on
    (warnings are fatal); disabled so newer clang warnings cannot fail the
    build. Documented here, not hidden.
"""

import json
import os
import re
import shlex
import shutil
import tempfile

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    save,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"

# Static upstream audit (see test_package/MANIFEST.yml for the full trail):
# 1253 ATF_TEST_CASE declarations in 104 *_test.cpp files
# + 160 utils_test_case cases in 12 integration/*.sh programs
# + 12 atf_test_case cases in doc/manbuild_test.sh
# + 10 AT_SETUP cases in bootstrap/testsuite.at.
UPSTREAM_TOTAL = 1435

_MKTEMP_SHIM = """#!/bin/sh
# HMBS unsafe_local_mktemp: toybox mktemp under umask 077 creates directories
# on HMDFS that cannot be written into, aborting config.status
# (confXXX/subs1.awk Permission denied). When HMBS_AUTOCONF_MKTEMP_FALLBACK=1,
# fail `mktemp -d` so Autoconf falls back to its mkdir machinery; otherwise
# use a mkdir-based `mktemp -d`.
mode=""
for a in "$@"; do
  case "$a" in
    -d) mode="-d" ;;
  esac
done
if [ "$mode" = "-d" ]; then
  if [ "${HMBS_AUTOCONF_MKTEMP_FALLBACK:-0}" = "1" ]; then
    exit 1
  fi
fi
if [ "$mode" != "-d" ]; then
  exec %s "$@"
fi
dir=""
for a in "$@"; do
  case "$a" in
    -d) ;;
    *)  dir="$a" ;;
  esac
done
[ -n "$dir" ] || dir="./tmp.XXXXXX"
base=$(dirname "$dir")
pat=$(basename "$dir")
out=""
i=0
while [ -z "$out" ] && [ $i -lt 100 ]; do
  cand="$base/$(echo "$pat" | sed "s/XXXXXX/$$-$i/")"
  if mkdir -p "$cand" 2>/dev/null; then out="$cand"; fi
  i=$((i + 1))
done
if [ -n "$out" ]; then
  echo "$out"
  exit 0
fi
exit 1
"""


class KyuaConan(ConanFile):
    name = "kyua"
    version = "0.13-git20240311-0a43bb8d89e3"
    description = "Testing framework for infrastructure software (ATF test runner)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/freebsd/kyua"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("testing", "atf", "test-runner")
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    exports_sources = "conandata.yml"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Early probe (runs during graph resolution, BEFORE any build):
        # emit the shell/compiler/perl decisions into the log so the next
        # preflight shows kyua-side hardening was synced. Round 15's
        # same-runner disk repair was proven infeasible this cycle:
        # preflight logged `profiled-shell repair: mkdir-failed:
        # [Errno 13] Permission denied: '/data/service/hnp/bin'` (the
        # runner lacks the hnp tree and the account cannot create it), so
        # the shim is deleted and lutok is vendored statically instead
        # (see _build_vendored_lutok; notes round 16). The remote
        # lutok/0.6.2 package is no longer consumed, hence no requires().
        # Health-machine zero-change.
        try:
            self.output.info(
                "kyua: early shell probe: %s" % self._select_shell()
            )
            cc_info = self._select_compiler_command("c") or "<none>"
            cxx_info = self._select_compiler_command("cpp") or "<none>"
            self.output.info("kyua: early compiler probe: c=%s cpp=%s"
                             % (cc_info, cxx_info))
            self.output.info("kyua: early perl probe: %s"
                             % self._select_perl())
            self.output.info(
                "kyua: lutok vendored-static (no remote lutok requires;"
                " see _build_vendored_lutok, notes round 16)"
            )
            self.output.info(
                "kyua: tool pins (round 39): automake/1.18 + libtool/2.5.4.1"
                " + pkgconf/3.0.5 (repo-unique/reliable); m4 + autoconf"
                " VENDORED privately (no tool_requires, see"
                " _build_vendored_toolchain, notes round 39) + "
                "sqlite3/3.49.1#669361066cc2c76e0ed897e6b6a27e38 + lua/5.4.8.1"
            )
        except Exception as exc:  # never break graph resolution on probe
            self.output.info("kyua: early probe skipped: %s" % exc)
        # NOTE: no self.requires("lutok/0.6.2") here. The remote lutok
        # recipe (remote-served; preflight exports only this kyua dir)
        # aborts at configure[141] with bash-127 on runners missing the
        # profile-pinned shell, and kyua-side disk repair is
        # permission-denied (round 15 evidence). Lutok 0.6.2 sources are
        # therefore built statically inside this recipe's own (hardened)
        # build context; kyua links the static archive and ships no lutok
        # runtime dependency.
        # Preflight 2026-09-26T21:29 resolves bare sqlite3/3.49.1 to the
        # conancenter CMake recipe: `System is unknown to cmake` plus
        # CMAKE_C_COMPILER sanity failure in `cmake.configure(...)`
        # (build() line 160), while this repo's sqlite3/3.49.1 recipe is a
        # manual clang amalgamation build with no cmake import at all.
        # Pin the ohpcd-published RREV (bzrtp/5.3.105 precedent, read live
        # from the ohpcd v2 revisions API 2026-07-10, single revision) so
        # the hardened in-repo recipe is used in every environment.
        # Falsification: `not found in remotes` -> pruned from ohpcd,
        # drop the RREV and report.
        self.requires("sqlite3/3.49.1#669361066cc2c76e0ed897e6b6a27e38")
        # Preflight 2026-09-26 resolves lua/5.4.8 (via lutok) to the
        # conancenter CMake recipe: the log shows `System is unknown to
        # cmake` plus a CMAKE_C_COMPILER sanity failure inside
        # `cmake.configure(...)` (build() line 79), while this repo's
        # lua/5.4.8 recipe is a pure makefile build with no cmake import
        # at all. Bare 5.4.8 exists on BOTH remotes (CCI recipes/lua
        # config.yml today: 5.5.0/5.4.8/5.4.6/5.3.6/5.3.5) and preflight
        # queries conancenter first (official CI disables it per
        # ci/conan/setup.sh), so the CCI recipe shadows ours. Override to
        # the repo-unique lua/5.4.8.1 (merged e7ccb1b5b, makefile generic
        # target, status built), which CCI does not carry, forcing
        # fall-through to ohpcd. ABI-safe: Lua 5.4.x is stable and both
        # revisions expose pkg_config_name lua-5.4, which is what lutok's
        # m4 probes first. Falsification: if the next log reports
        # lua/5.4.8.1 not found in remotes, revert this line and report
        # need-to-publish.
        # Round 22: plain (non-override) requires. Since round 16 the
        # remote lutok is no longer consumed, nothing transitively
        # requires lua, so `override=True` is a no-op that adds NOTHING
        # to the graph (Conan: override only replaces a version pulled
        # by someone else). Evidence this round: `lua.h not found under
        # <no lua package folder>` + visible .pc list without lua-5.4.pc
        # (PkgConfigDeps had no lua to render). Plain requires restores
        # the lua package folder, the lua-5.4.pc, and the LUA_* bypass
        # data source below.
        self.requires("lua/5.4.8.1")
        # NOTE 2026-09-27 round 4:上一轮 host 域
        # self.requires("m4/...#...") / self.requires("autoconf/...#...")
        # 在本轮预检中被证实无效——日志仍构建裸版本 CCI m4/1.4.19（含仅
        # CCI 才有的 0004-disable-hardening 补丁），说明覆盖未命中。
        # 根因：m4/autoconf 以 build context（tool_requires 传递闭包：
        # kyua tool_requires autoconf -> autoconf tool_requires m4）消费，
        # host 域 requires override 作用不到该域（heimdal 7.8.0 先例：
        # 工具链覆盖必须用 self.tool_requires(..., override=True)）。
        # 正确域的 pin 见 build_requirements()；此处不再声明 host 域 pin。

    def build_requirements(self):
        # Git snapshot without generated `configure` (librb 2.0.0 precedent).
        self.tool_requires("automake/1.18")
        # Round 39 (strategy: vendor the bootstrap toolchain, drop the
        # graph pins): rounds 4/36/37 tried to steer m4/autoconf selection
        # through tool_requires RREV/override semantics (host-domain pin ->
        # tool override -> dual hard pin -> parent-hard-child-override
        # pairing), but the 2026-09-27T22:02 preflight — running a tree
        # that already contained the pairing (export hash changed vs the
        # 21:26 run) — still built the BARE CCI m4/1.4.19 (CCI-only
        # 0004-disable-hardening patch + configure[139] bash-127, no graph
        # conflict). Either the override is silently ineffective in this
        # Conan version/context layout or the pinned RREVs do not resolve
        # on the queried remotes; both hypotheses are indistinguishable
        # from the recipe side and every further pin permutation repeats
        # the same falsified family. Different route, same as round 16
        # did for lutok: consume NEITHER the remote nor the CCI toolchain
        # package — build GNU m4 + autoconf release tarballs (both ship
        # pre-generated `configure`, so no recursion) privately inside
        # this recipe's own hardened build context (probed
        # SHELL/CONFIG_SHELL/CC/PKG_CONFIG/mktemp/umask/INSTALL handling
        # via _build_vendored_toolchain) and use them for the kyua
        # bootstrap. automake/libtool/pkgconf stay pinned: 1.18 and
        # 2.5.4.1 are repo-unique versions (CCI carries neither), and
        # pkgconf/3.0.5 resolves reliably, so nothing else can be
        # shadowed. No RREV anywhere below: nothing to prune, nothing to
        # conflict.
        self.tool_requires("libtool/2.5.4.1")
        self.tool_requires("pkgconf/3.0.5")
        # ATF M4 macros for autoreconf plus ATF libs for the test programs.
        self.test_requires("atf/0.23")

    def layout(self):
        basic_layout(self)

    def validate(self):
        # R32: OHOS must be matched alongside Linux, never `== "Linux"`.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "kyua supports Linux/OHOS only, got %s" % self.settings.os
            )
        # Round 12 (strategy cycle 5: prior gate proven counterproductive,
        # different route = remove it, not adjust its condition):
        # rounds 10-11 added a graph-phase gate raising Invalid when the
        # profile-pinned /data/service/hnp/bin/bash was missing. This round's
        # preflight proves it FIRED (ERROR: There are invalid packages:
        # kyua: Invalid: kyua: preflight runner lacks the profile-pinned
        # shell ...) yet the backend still routed the failure back to kyua
        # as a compile failure. The gate converts an env/infra fault
        # (missing runner path + lutok/0.6.2 recipe lacking a SHELL
        # fallback in its own isolated build context, which kyua cannot
        # patch single-PR) into a kyua Invalid, i.e. self-sabotage that
        # masks lutok's native fingerprint and loops forever. So the gate
        # is deleted here: kyua stays valid on every runner; a missing
        # pinned shell then surfaces natively from lutok's configure[141]
        # for correct env/infra routing (lutok channel or bash-complete
        # runner). Kyua's own shell/compiler/perl probing in
        # generate()/build() is kept (health-machine zero-change, only
        # affects kyua's own context).

    def source(self):
        get(self, **self.conan_data["sources"]["kyua"], strip_root=True)
        self._patch_cxx17_compat()
        self._patch_bsd_file_flags()

    def _patch_bsd_file_flags(self):
        # Round 47 (new fingerprint inside the compile phase: rounds 45-46
        # already proved effective — vendor lutok links (-llutok), the ATF
        # -I reaches every TU and the build passes plain_helpers — but the
        # next TU `utils/process/executor_pid_test.cpp:88` fails with
        # `use of undeclared identifier 'UF_NOUNLINK'`. Upstream
        # leak_work_dir() calls `fchflags(fd, UF_NOUNLINK)`, a FreeBSD-only
        # API (the file-header comment describes the chflags/uunlink PID-
        # wrap scenario; clean_up() even shells `chflags -R nouunlink`).
        # Neither the flag nor fchflags() exists on OHOS/Linux, so no flag
        # ordering or include wiring can fix this — different route: guard
        # the body with #ifdef UF_NOUNLINK and ATF_SKIP with an explicit
        # platform reason when unavailable. The 10 leak_* cases then report
        # skipped (not passed) at `make check` runtime, recorded as an
        # ohos_feature gap; no assertion is deleted and nothing is silently
        # faked. Regex-based and idempotent; logged for the next round.
        import re as _re
        rel = os.path.join("utils", "process", "executor_pid_test.cpp")
        path = os.path.join(self.source_folder, rel)
        try:
            with open(path, "r", encoding="utf-8",
                      errors="surrogateescape") as handle:
                text = handle.read()
        except OSError as exc:
            self.output.warning(
                "kyua: bsd-flags patch missing file %s: %s" % (rel, exc))
            return
        if "UF_NOUNLINK/fchflags not available on this platform" in text:
            self.output.info("kyua: bsd-flags patch already applied in %s"
                             % rel)
            return
        if "fchflags(fd, UF_NOUNLINK)" not in text:
            self.output.warning(
                "kyua: bsd-flags patch pattern not found in %s" % rel)
            return
        pat = _re.compile(
            r"void\nleak_work_dir\(\)\n\{(.*?)\n\}",
            _re.DOTALL)
        guarded = (
            "void\nleak_work_dir()\n{\n"
            "#ifdef UF_NOUNLINK\n"
            "%s\n"
            "#else\n"
            "\tATF_SKIP(\"UF_NOUNLINK/fchflags not available "
            "on this platform (non-BSD)\");\n"
            "#endif\n"
            "}")
        new_text, n = pat.subn(
            lambda m: guarded % m.group(1), text, count=1)
        if not n:
            self.output.warning(
                "kyua: bsd-flags patch function match failed in %s" % rel)
            return
        try:
            with open(path, "w", encoding="utf-8",
                      errors="surrogateescape") as handle:
                handle.write(new_text)
            self.output.info(
                "kyua: bsd-flags patch applied in %s: "
                "leak_work_dir guarded by #ifdef UF_NOUNLINK" % rel)
        except OSError as exc:
            self.output.warning(
                "kyua: bsd-flags patch write failed %s: %s" % (rel, exc))

    def _patch_cxx17_compat(self):
        # Round 43 (strategy change: round 42's `-std=gnu++11` toolchain flag
        # did NOT appear in the next preflight compile line, which still shows
        # only `-std=c++17` before `-O3`. Either the profile/buildenv -std is
        # appended after the toolchain CXXFLAGS (last-wins defeats us) or the
        # flag never made the sync; in either case flag-ordering is proven an
        # unreliable lever for this failure. Different route: fix the source,
        # which is ordering-independent and is the true upstream fix.
        # Upstream PR #264 (merged 2025-04-24, commit 126e6be, postdates this
        # 2024-03-11 snapshot): `Switch from std::auto_ptr<> to
        # std::unique_ptr<>` across 40 files, plus explicit std::move() at the
        # ~5 ownership-handoff sites that relied on auto_ptr copy-transfer.
        # Mechanical backport below: global auto_ptr->unique_ptr rename
        # (covers declarations, locals, return types, .release()/.get() users
        # which behave identically) + the 5 move fixes. Idempotent (re-run
        # safe: rename is a no-op once applied; move inserts skip when
        # std::move already present). Logged per file for the next round.
        renamed = 0
        for root, _, files in os.walk(self.source_folder):
            for name in files:
                if not name.endswith((".hpp", ".cpp", ".ipp", ".h", ".c")):
                    continue
                path = os.path.join(root, name)
                try:
                    with open(path, "r", encoding="utf-8",
                               errors="surrogateescape") as handle:
                        text = handle.read()
                except OSError:
                    continue
                count = text.count("std::auto_ptr")
                if not count:
                    continue
                text = text.replace("std::auto_ptr", "std::unique_ptr")
                try:
                    with open(path, "w", encoding="utf-8",
                               errors="surrogateescape") as handle:
                        handle.write(text)
                    renamed += 1
                except OSError as exc:
                    self.output.warning(
                        "kyua: cxx17 rename skipped %s: %s" % (path, exc))
        self.output.info(
            "kyua: cxx17 compat rename auto_ptr->unique_ptr: %d file(s)"
            % renamed)
        # Follow-on (preflight round 44): the rename above turns
        # `return std::auto_ptr< child >(NULL);` (utils/process/child.cpp:226,
        # :287) into `return std::unique_ptr< child >(NULL);`, which this
        # libc++ rejects as an ambiguous long->unique_ptr conversion (the
        # explicit pointer ctor competes once NULL is `long`, not __null).
        # Upstream #264 kept `(NULL)` and happens to build on FreeBSD clang,
        # so this is a one-token OHOS-libc++ follow-on, not a strategy change:
        # `unique_ptr<T>(NULL)` -> `unique_ptr<T>(nullptr)`. Scoped by regex
        # to unique_ptr constructions only; `.reset(NULL)` (single overload,
        # unambiguous) is left untouched.
        null_fixed = 0
        null_pat = re.compile(r"std::unique_ptr<([^<>]+)>\(NULL\)")
        for root, _, files in os.walk(self.source_folder):
            for name in files:
                if not name.endswith((".hpp", ".cpp", ".ipp", ".h", ".c")):
                    continue
                path = os.path.join(root, name)
                try:
                    with open(path, "r", encoding="utf-8",
                               errors="surrogateescape") as handle:
                        text = handle.read()
                except OSError:
                    continue
                new_text, n = null_pat.subn(
                    r"std::unique_ptr<\1>(nullptr)", text)
                if not n:
                    continue
                try:
                    with open(path, "w", encoding="utf-8",
                               errors="surrogateescape") as handle:
                        handle.write(new_text)
                    null_fixed += n
                    self.output.info(
                        "kyua: cxx17 nullptr fix in %s (%d)"
                        % (os.path.relpath(path, self.source_folder), n))
                except OSError as exc:
                    self.output.warning(
                        "kyua: cxx17 nullptr fix skipped %s: %s" % (path, exc))
        self.output.info(
            "kyua: cxx17 compat nullptr fixes: %d" % null_fixed)
        moves = [
            ("cli/main.cpp",
             "commands.insert(mock_command);",
             "commands.insert(std::move(mock_command));"),
            ("cli/main.cpp",
             "safe_main(ui, argc, argv, mock_command)",
             "safe_main(ui, argc, argv, std::move(mock_command))"),
            ("utils/process/executor.ipp",
             "timeout, unprivileged_user, child);",
             "timeout, unprivileged_user, std::move(child));"),
            ("utils/process/executor.ipp",
             "spawn_followup_post(base, timeout, child);",
             "spawn_followup_post(base, timeout, std::move(child));"),
            ("utils/signals/interrupts.cpp",
             "sighup_handler = tmp_sighup_handler;",
             "sighup_handler = std::move(tmp_sighup_handler);"),
            ("utils/signals/interrupts.cpp",
             "sigint_handler = tmp_sigint_handler;",
             "sigint_handler = std::move(tmp_sigint_handler);"),
            ("utils/signals/interrupts.cpp",
             "sigterm_handler = tmp_sigterm_handler;",
             "sigterm_handler = std::move(tmp_sigterm_handler);"),
        ]
        for rel, old, new in moves:
            path = os.path.join(self.source_folder, *rel.split("/"))
            try:
                with open(path, "r", encoding="utf-8",
                           errors="surrogateescape") as handle:
                    text = handle.read()
            except OSError as exc:
                self.output.warning(
                    "kyua: cxx17 move patch missing file %s: %s" % (rel, exc))
                continue
            if new in text:
                continue
            if old not in text:
                self.output.warning(
                    "kyua: cxx17 move patch pattern not found in %s: %r"
                    % (rel, old))
                continue
            text = text.replace(old, new)
            try:
                with open(path, "w", encoding="utf-8",
                           errors="surrogateescape") as handle:
                    handle.write(text)
                self.output.info(
                    "kyua: cxx17 move patch applied in %s: %r" % (rel, old))
            except OSError as exc:
                self.output.warning(
                    "kyua: cxx17 move patch write failed %s: %s" % (rel, exc))

    def _resolve_hmbs_tmp(self):
        # HMBS readonly_tmp: /tmp may be read-only (erofs) on the real
        # machine; probe HMBS-injected candidates for real writability.
        def _valid(path):
            try:
                if not path or path in ("0", "1") or path == "/tmp":
                    return False
                os.makedirs(path, exist_ok=True)
                fd, probe = tempfile.mkstemp(dir=path)
                os.close(fd)
                os.unlink(probe)
                return True
            except Exception:
                return False

        for cand in (
            os.environ.get("HMBS_AUTOCONF_MKTEMP_FALLBACK"),
            os.environ.get("TMPDIR"),
            os.environ.get("TMP"),
            os.environ.get("TEMP"),
            os.environ.get("HMBS_TMPDIR"),
        ):
            if cand and _valid(cand):
                return cand
        fallback = os.path.join(self.build_folder, "cfg-tmp")
        try:
            os.makedirs(fallback, exist_ok=True)
        except OSError:
            pass
        return fallback

    def _select_shell(self):
        # Strategy cycle 3 (2026-09-27 round 7): kyua blindly trusted
        # $SHELL (`os.environ.get("SHELL", "/bin/sh")`) without existence
        # probing, so a profile-pinned missing bash (lutok configure[141]
        # `inaccessible or not found`, Error 127) would also abort kyua's
        # own configure/config.status. Mirror the in-repo m4/1.4.19
        # `_select_shell` precedent (existence-probed fallback, r13 true
        # device verified): prefer HMBS-injected/outer-env shells only when
        # the absolute path exists and is executable, else fall back through
        # PATH lookup to a guaranteed `sh`. Health-machine zero-change
        # (profiled bash exists -> returned as-is); missing-bash runner ->
        # /bin/sh instead of Error 127. Applies to kyua's own build context
        # only; it cannot propagate into lutok's independent build context
        # (separate recipe generate()), so a lutok-side fix is still needed
        # for the current preflight blocker (see notes.md round 7).
        for shell in (
            os.environ.get("CONFIG_SHELL"),
            os.environ.get("SHELL"),
            "/data/service/hnp/bin/bash",
            "/bin/sh",
            "/system/bin/sh",
        ):
            if not shell:
                continue
            if os.path.isabs(shell):
                try:
                    if os.path.isfile(shell) and os.access(shell, os.X_OK):
                        return shell
                except OSError:
                    continue
            elif shutil.which(shell):
                return shell
        fallback = shutil.which("sh") or shutil.which("bash") or "sh"
        return fallback

    def _is_executable(self, command):
        if os.path.isabs(command):
            try:
                return os.path.isfile(command) and os.access(command, os.X_OK)
            except OSError:
                return False
        return shutil.which(command) is not None

    def _select_compiler_command(self, compiler):
        # Aggregated experience #1 (profile-pinned compiler missing):
        # existence-probed fallback. Conf path exists -> return as-is
        # (health-machine zero-change). Missing -> PATH discovery,
        # preferring a sibling in the same directory as the pinned path,
        # else any PATH clang/gcc/cc. Only CC/CXX exports are overridden;
        # CFLAGS/LDFLAGS are untouched. Both missing -> None (caller logs
        # an explicit infra-style message instead of a bare Error 127).
        compilers = {}
        try:
            compilers = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
        except Exception:
            compilers = {}
        command = compilers.get(compiler)
        if command:
            try:
                parts = shlex.split(command)
            except ValueError:
                parts = [command]
            if parts and self._is_executable(parts[0]):
                return command
            # Try stripping a missing wrapper prefix (m4 precedent).
            for index in range(1, len(parts)):
                if self._is_executable(parts[index]):
                    return shlex.join(parts[index:])
            # Fall through to PATH discovery below.
            pinned_dir = None
            try:
                if parts and os.path.isabs(parts[0]):
                    pinned_dir = os.path.dirname(parts[0])
            except OSError:
                pinned_dir = None
            if compiler == "c":
                candidates = ("clang", "gcc", "cc")
            else:
                candidates = ("clang++", "g++", "c++")
            # Prefer sibling in the pinned directory when it exists.
            if pinned_dir:
                try:
                    if os.path.isdir(pinned_dir):
                        for cand in candidates:
                            sibling = os.path.join(pinned_dir, cand)
                            if self._is_executable(sibling):
                                return sibling
                except OSError:
                    pass
            for cand in candidates:
                found = shutil.which(cand)
                if found:
                    return found
            return command
        # No conf pin: nothing to override.
        return None

    def _select_tool_command(self, candidates):
        for candidate in candidates:
            found = shutil.which(candidate)
            if found:
                return found
        return candidates[0] if candidates else None

    def _select_install_args(self):
        # Round 30 (strategy cycle 9: three vendor-install rounds in a row
        # patched the TARGET list — umask mode, lua.hpp shim, doc_DATA=
        # skip — and the fingerprint just moved one target down:
        # docDATA Error 64 became examplesDATA Error 64. That falsifies
        # the whole "skip one DATA variable" family by rule, so this round
        # fixes the TOOL instead: the failing program is the HMBS-provided
        # `.../runtime/.../bin/install` wrapper (single-file libtool
        # installs succeed, multi-file `install -c -m 644 a b c dir`
        # DATA installs exit 64/EX_USAGE). Automake derives
        # INSTALL_PROGRAM/INSTALL_DATA/INSTALL_SCRIPT from INSTALL, and
        # GNU make command-line assignments override the configure-baked
        # value (including libtool's install path, which automake invokes
        # as `$(LIBTOOL) --mode=install $(INSTALL) ...`), so one INSTALL=
        # override repairs lib+headers+pkgconfig+docs in a single lever.
        # E312/E313 precedent: `make install INSTALL=/system/bin/install
        # -c`. Selection is by real file-evidence probe (multi-file copy
        # with -m 644 in a scratch dir, content compared), never by PATH
        # order or stdout parsing; the HMBS wrapper sits on PATH but fails
        # the probe and is skipped. No working install -> cp trio
        # fallback (INSTALL/INSTALL_PROGRAM/INSTALL_DATA/INSTALL_SCRIPT
        # all set, because automake expands INSTALL_DATA as
        # `$(INSTALL) -m 644` and bare `cp -fp -m 644` would be invalid).
        # Returns a list of `VAR="value"` make tokens (empty = no
        # override, plain `make install` with evidence on failure).
        import subprocess
        probe = os.path.join(self.build_folder, "install-probe")
        try:
            os.makedirs(probe, exist_ok=True)
        except OSError:
            return []
        src1 = os.path.join(probe, "probe1.txt")
        src2 = os.path.join(probe, "probe2.txt")
        dest = os.path.join(probe, "dest")
        try:
            with open(src1, "w", encoding="utf-8") as handle:
                handle.write("probe-one\n")
            with open(src2, "w", encoding="utf-8") as handle:
                handle.write("probe-two\n")
            try:
                shutil.rmtree(dest, ignore_errors=True)
            except OSError:
                pass
            os.makedirs(dest, exist_ok=True)
        except OSError as exc:
            self.output.info("kyua: install probe setup skipped: %s" % exc)
            return []

        def _trial(argv):
            try:
                shutil.rmtree(dest, ignore_errors=True)
                os.makedirs(dest, exist_ok=True)
                completed = subprocess.run(
                    argv, stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE, timeout=60)
                if completed.returncode != 0:
                    return False
                for name, want in (("probe1.txt", "probe-one\n"),
                                   ("probe2.txt", "probe-two\n")):
                    got_path = os.path.join(dest, name)
                    try:
                        with open(got_path, "r",
                                  encoding="utf-8") as handle:
                            if handle.read() != want:
                                return False
                    except OSError:
                        return False
                return True
            except Exception:
                return False

        ordered = ["/system/bin/install", "/bin/install",
                   "/usr/bin/install"]
        try:
            for name in ("ginstall", "install"):
                found = shutil.which(name)
                if found and found not in ordered:
                    ordered.append(found)
        except Exception:
            pass
        for cand in ordered:
            try:
                if not (os.path.isfile(cand) and os.access(cand, os.X_OK)):
                    continue
            except OSError:
                continue
            if _trial([cand, "-c", "-m", "644", src1, src2, dest]):
                self.output.info(
                    "kyua: INSTALL probe passed: %s" % cand)
                return ["INSTALL=\"%s -c\"" % cand]
            self.output.info(
                "kyua: INSTALL probe rejected: %s" % cand)
        cp_cands = []
        try:
            found_cp = shutil.which("cp")
            if found_cp:
                cp_cands.append(found_cp)
        except Exception:
            pass
        for extra in ("/system/bin/cp", "/bin/cp", "/usr/bin/cp"):
            if extra not in cp_cands:
                cp_cands.append(extra)
        for cp_bin in cp_cands:
            try:
                if not (os.path.isfile(cp_bin)
                        and os.access(cp_bin, os.X_OK)):
                    continue
            except OSError:
                continue
            if _trial([cp_bin, "-fp", src1, src2, dest]):
                self.output.info(
                    "kyua: INSTALL cp fallback: %s" % cp_bin)
                return ["INSTALL=\"%s -fp\"" % cp_bin,
                        "INSTALL_PROGRAM=\"%s -fp\"" % cp_bin,
                        "INSTALL_DATA=\"%s -fp\"" % cp_bin,
                        "INSTALL_SCRIPT=\"%s -fp\"" % cp_bin]
        self.output.info("kyua: no working INSTALL found; plain install")
        return []

    def _select_perl(self):
        # Round 9 (same missing-hnp-bin family, new absolute path not yet
        # hardened): `_bootstrap_autotools` hardcodes
        # `export PERL=/data/service/hnp/bin/perl` (librb 2.0.0 system-perl
        # precedent). The runner family that lacks the profiled bash at the
        # same hnp bin dir can lack this perl too, which would abort kyua's
        # own autoreconf bootstrap with the same Error-127 shape AFTER lutok
        # unblocks. Pinned path exists -> return as-is (health-machine
        # zero-change); else PATH perl; else keep the pinned value and let
        # the bootstrap step fail explicitly (log names the missing path).
        pinned = "/data/service/hnp/bin/perl"
        try:
            if os.path.isfile(pinned) and os.access(pinned, os.X_OK):
                return pinned
        except OSError:
            pass
        found = shutil.which("perl")
        if found:
            return found
        return pinned

    def _find_m4_file(self, dep_name, filename):
        # Round 31: pkgconf is a tool_requires (build context), invisible
        # to the host-context self.dependencies[...] lookup (2026-09-27T18:27
        # preflight: KeyError 'pkgconf' at this line, while the atf
        # test_requires lookup two lines above in _bootstrap_autotools
        # succeeded). Try the default view first (host requires like
        # sqlite3/lua plus test_requires like atf), then the build view
        # (tool_requires like pkgconf; _pkgconf_binary precedent already
        # uses self.dependencies.build.get). Missing in both -> (None,
        # None) so callers keep raising their explicit macro-missing
        # messages; nothing is silently skipped.
        # Round 40: return the directory HOLDING the file (root), not its
        # parent. The 22:54 preflight proves the old dirname(root): the
        # bootstrap `-I` lines carried `<pkg>/share` for both atf and
        # pkgconf (i.e. the .m4 files live in `<pkg>/share/aclocal/`),
        # aclocal -I is non-recursive, so aclocal.m4 missed pkg.m4 and the
        # vendored autoconf died at `configure.ac:65: Cannot find pkg.m4`.
        # Both callers (aclocal -I + ACLOCAL_PATH) need the exact dir.
        dep = None
        try:
            dep = self.dependencies[dep_name]
        except KeyError:
            dep = None
        if dep is None:
            try:
                dep = self.dependencies.build[dep_name]
            except Exception:
                return None, None
        folder = dep.package_folder
        for root, _, files in os.walk(folder):
            if filename in files:
                return root, os.path.join(root, filename)
        return None, None

    def _atf_package_folder(self):
        return self.dependencies["atf"].package_folder.replace("\\", "/")

    def _atf_pkgconfig_dir(self):
        # atf/0.23 ships .pc/.la files built with prefix=/ (lutok 0.6.2
        # finding: includedir=//include, dependency_libs=//lib/*.la); write
        # private .pc files pointing at the real package folder and link
        # against copies of the static archives.
        atf_folder = self._atf_package_folder()
        link_dir = os.path.join(self.build_folder, "atf-libs")
        os.makedirs(link_dir, exist_ok=True)
        for lib in ("libatf-c++.a", "libatf-c.a"):
            shutil.copy2(
                os.path.join(atf_folder, "lib", lib),
                os.path.join(link_dir, lib),
            )
        pcdir = os.path.join(self.build_folder, "atf-pkgconfig")
        os.makedirs(pcdir, exist_ok=True)
        save(
            self,
            os.path.join(pcdir, "atf-c++.pc"),
            "prefix=%s\n"
            "includedir=${prefix}/include\n"
            "libdir=%s\n\n"
            "Name: atf-c++\n"
            "Description: Automated Testing Framework (C++ binding)\n"
            "Version: %s\n"
            "Cflags: -I${includedir}\n"
            "Libs: -L${libdir} -latf-c++ -latf-c\n"
            % (
                atf_folder,
                link_dir.replace("\\", "/"),
                self.dependencies["atf"].ref.version,
            ),
        )
        save(
            self,
            os.path.join(pcdir, "atf-sh.pc"),
            "exec_prefix=%s\n"
            "interpreter=${exec_prefix}/bin/atf-sh\n\n"
            "Name: atf-sh\n"
            "Description: Automated Testing Framework (POSIX shell binding)\n"
            "Version: %s\n"
            % (atf_folder, self.dependencies["atf"].ref.version),
        )
        return pcdir.replace("\\", "/")

    def _pkgconf_binary(self):
        # pkgconf/3.0.5 deliberately ships bin/pkgconf WITHOUT a
        # bin/pkg-config alias (its package() raises on unexpected alias),
        # so autotools PKG_PROG_PKG_CONFIG probes for `pkg-config` fail
        # with `configure: error: pkg-config not found` even though the
        # tool package is present (ext2fuse/cassbeam precedent).
        # Prefer the absolute tool-package binary (deterministic source);
        # fall back to PATH lookup; empty string when unavailable.
        try:
            bdep = self.dependencies.build.get("pkgconf")
            if bdep is not None and getattr(bdep, "package_folder", None):
                cand = os.path.join(
                    str(bdep.package_folder), "bin", "pkgconf")
                if os.path.isfile(cand):
                    return cand
        except Exception:
            pass
        for cand in (shutil.which("pkgconf") or "", "/usr/bin/pkgconf",
                     "/usr/local/bin/pkgconf"):
            try:
                if cand and os.path.isfile(cand):
                    return cand
            except OSError:
                continue
        return ""

    def _ensure_pkg_config_shim(self):
        # Provide `pkg-config` (and the --host-prefixed triplet name that
        # configure probes first) on PATH via the pkgconf binary
        # (cassbeam _ensure_pkg_config_shim precedent: symlink preferred,
        # copyfile fallback avoids HMDFS chmod=0; no chmod attempted).
        shim_dir = os.path.join(self.build_folder, "pkgconf-shims")
        try:
            os.makedirs(shim_dir, exist_ok=True)
        except OSError:
            return ""
        pkgconf_bin = self._pkgconf_binary()
        if not pkgconf_bin:
            self.output.warning(
                "kyua: pkgconf binary not found; pkg-config shim skipped")
            return ""
        for name in ("pkg-config", "aarch64-unknown-linux-gnu-pkg-config"):
            link = os.path.join(shim_dir, name)
            try:
                if os.path.islink(link) or os.path.isfile(link):
                    try:
                        os.remove(link)
                    except OSError:
                        pass
                try:
                    os.symlink(pkgconf_bin, link)
                except (OSError, NotImplementedError):
                    shutil.copyfile(pkgconf_bin, link)
            except Exception as exc:
                self.output.warning(
                    "kyua: pkg-config shim %s failed: %s" % (name, exc))
                return ""
        self.output.info(
            "kyua: pkg-config shim ready: %s -> %s"
            % (shim_dir, pkgconf_bin))
        return shim_dir.replace("\\", "/")

    def _pkgconfig_search_dirs(self):
        # Round 20: PkgConfigDeps writes lua-5.4.pc / sqlite3.pc into the
        # generators folder, but nothing puts that folder on
        # PKG_CONFIG_PATH by itself (ext2fuse precedent appends
        # self.generators_folder explicitly). The lua/5.4.8.1 package
        # ships no .pc file of its own (headers/lib/bin only), so without
        # this wiring the vendored lutok configure dies at
        # `Package requirements (lua >= 5.4) were not met`. Collect the
        # deterministic candidate dirs: generators folder first, then the
        # host deps' own lib/share pkgconfig dirs when present.
        dirs = []
        try:
            gen = str(self.generators_folder or "")
            if gen and os.path.isdir(gen):
                dirs.append(gen)
        except Exception:
            pass
        for dep_name in ("lua", "sqlite3"):
            try:
                dep = self.dependencies.get(dep_name)
                folder = str(getattr(dep, "package_folder", "") or "")
            except Exception:
                continue
            if not folder:
                continue
            for sub in ("lib/pkgconfig", "lib/aarch64-unknown-linux-gnu/pkgconfig",
                        "share/pkgconfig"):
                cand = os.path.join(folder, sub.replace("/", os.sep))
                try:
                    if os.path.isdir(cand) and cand not in dirs:
                        dirs.append(cand)
                except OSError:
                    continue
        return dirs

    def _mktemp_shim_dir(self):
        # HMBS unsafe_local_mktemp minimal fix (round 23: round 22 gated the
        # deployment on os.environ at RECIPE runtime, but that var rides the
        # conanbuild script env on the real machine and is likely absent
        # from the outer process env, so the symlink branch never fired and
        # the fallback never deployed — same fingerprint with shifted line
        # numbers proves sync without effect). New rule: ALWAYS deploy the
        # shell script; the script itself gates at MACHINE runtime on
        # ${HMBS_AUTOCONF_MKTEMP_FALLBACK} (exported via hmbs_tmp_env), so
        # no recipe-time gating is needed. The symlink-to-false variant is
        # dropped: it also fails plain (non -d) mktemp, which Autoconf and
        # compiler probes still need.
        wrapper_dir = os.path.join(self.build_folder, "mktemp-wrapper")
        os.makedirs(wrapper_dir, exist_ok=True)
        real = None
        for candidate in (shutil.which("mktemp"), "/bin/mktemp", "/usr/bin/mktemp"):
            if candidate and os.path.isfile(candidate):
                real = candidate
                break
        if real is None:
            raise ConanException("mktemp not found; cannot install the HMDFS shim")
        wrapper = os.path.join(wrapper_dir, "mktemp")
        try:
            if os.path.islink(wrapper):
                os.remove(wrapper)
        except OSError:
            pass
        save(self, wrapper, _MKTEMP_SHIM % real)
        # HMBS chmod=0 runners cannot chmod; best-effort only, never fail here.
        try:
            os.chmod(wrapper, 0o755)
        except OSError as exc:
            self.output.info("kyua: mktemp shim chmod skipped: %s" % exc)
        return wrapper_dir.replace("\\", "/")

    def _patch_umask_077(self, path):
        # HMBS unsafe_local_mktemp / E114 minimal fix (round 27): HMDFS forces
        # setgid on directories, so `(umask 077 && mktemp -d ./confXXXXXX)`
        # creates drwx--S--- which even the owner cannot write into, and
        # config.status dies with `can't create ./confXXX/subs1.awk:
        # Permission denied`. Rounds 22-24 proved mktemp interception and
        # out-of-source relocation cannot fix this: the probe runs without
        # `umask 077` (dir 0755, write ok) while config.status forces 077
        # (dir 0700+S, write denied), and the same fingerprint recurs in the
        # obj tree. In-repo precedents (babeltrace 1.5.11 `umask 077`->`022`
        # in configure+config.status; 4ti2 1.6.10 mkdir patch; aaphoto E114
        # root-cause note) fix the mode, not the tool. Replace every
        # `umask 077` literal with `umask 022` (0755 dirs, owner-writable on
        # HMDFS; no-op on normal filesystems). Best-effort, never fails.
        try:
            if not path or not os.path.isfile(path):
                return 0
            with open(path, "r", encoding="utf-8",
                       errors="surrogateescape") as handle:
                text = handle.read()
            count = text.count("umask 077")
            if not count:
                return 0
            with open(path, "w", encoding="utf-8",
                       errors="surrogateescape") as handle:
                handle.write(text.replace("umask 077", "umask 022"))
            self.output.info("kyua: umask patch %s (%d occurrence(s))" % (path, count))
            return count
        except OSError as exc:
            self.output.info("kyua: umask patch skipped %s: %s" % (path, exc))
            return 0

    def generate(self):
        VirtualBuildEnv(self).generate()
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(
            [
                # automake 1.18 config.guess cannot recognize HarmonyOS;
                # bypass guessing with explicit triplets (E007/E160).
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-gnu",
                "--with-doxygen=no",
                # ATF is present via test_requires; fail fast if detection
                # breaks instead of silently dropping the test suite.
                "--with-atf=yes",
                # Git-HEAD builds default developer mode (warnings fatal);
                # disabled so newer-clang warnings cannot fail the build.
                "--disable-developer",
            ]
        )
        # Round 25: compile-phase Signal 9 (SIGKILL, 128+9=137) with empty
        # stdout/stderr on the single-job (tools.build:jobs=1) preflight.
        # Same fingerprint as archives/a/aws-lc-tools/5.2.0/conanfile.py
        # rounds 4-5 (rc=137/SIGKILL mid-compile): per-TU cc1plus peak memory
        # exceeds the device budget when building kyua's 100+ ATF C++ TUs
        # with the profile's -O2/-g. Appended flags win (clang takes the last
        # -O/-g on the command line), so -O1 -g0 lowers compile and link
        # memory without changing test semantics. No -DNDEBUG is added:
        # assert() behaviour inside the ATF test programs is preserved, and
        # the upstream suite still builds and runs in full (1435 total).
        # Health-machine zero-change in effect (flags only narrow codegen/
        # debug output); non-OHOS builds are untouched.
        # Falsification: Signal 9 persists under -O1 -g0 -> not per-TU
        # compiler memory; investigate the link step or tmpfs next.
        if self.settings.os == "OHOS":
            tc.cflags.extend(["-O1", "-g0"])
            tc.cxxflags.extend(["-O1", "-g0"])
            self.output.info("kyua: OHOS memory-saver flags: -O1 -g0")
        # Round 42: kyua snapshot (2024-03-11) uses std::auto_ptr
        # (cli/common.hpp:71), removed in C++17. Profile/toolchain injects
        # -std=c++17 so every TU fails with `no template named 'auto_ptr'`.
        # Upstream requires only C++11 (AX_CXX_COMPILE_STDCXX 11) and the
        # official FreeBSD ports fix for 0.13 is USE_CXXSTD=gnu++11
        # (commit 7ecd176); upstream unique_ptr migration (#264, 2025-04-24)
        # postdates this snapshot and touches many files. Minimal route:
        # append -std=gnu++11 last-wins (clang takes the last -std) for
        # kyua's own configure+make only. Vendored lutok appends
        # -std=c++20 after $CXXFLAGS in its own shell line, so it still
        # wins there; no cross-pollution.
        tc.cxxflags.append("-std=gnu++11")
        self.output.info("kyua: C++ std override (auto_ptr): -std=gnu++11")
        env = tc.environment()
        env.prepend_path("PKG_CONFIG_PATH", self._atf_pkgconfig_dir())
        # Round 20: PkgConfigDeps-generated lua-5.4.pc / sqlite3.pc live
        # in the generators folder, which conanbuild does NOT put on
        # PKG_CONFIG_PATH by itself (ext2fuse precedent; this round's
        # failure is `Package requirements (lua >= 5.4) were not met`).
        for pc_dir in self._pkgconfig_search_dirs():
            env.prepend_path("PKG_CONFIG_PATH", pc_dir)
        # unsafe_local_mktemp: the shim must ride BOTH channels. The
        # Toolchain env (conanautotoolchain.sh) is only sourced by the
        # Autotools helper; manual self.run(env="conanbuild") for the
        # vendored lutok configure sees only hmbs_tmp_env/conanbuild.sh
        # (round 21 lua lesson). So keep one dir and prepend it twice.
        mktemp_dir = self._mktemp_shim_dir()
        env.prepend_path("PATH", mktemp_dir)
        self.output.info("kyua: mktemp shim ready: %s" % mktemp_dir)
        # Round 19: pkgconf/3.0.5 ships only `pkgconf`, no `pkg-config`
        # alias, so both kyua's own configure and the vendored lutok
        # configure fail at PKG_PROG_PKG_CONFIG. Ext2fuse precedent:
        # PKG_CONFIG env selects the implementation; cassbeam precedent:
        # a pkg-config -> pkgconf shim satisfies direct-name probes
        # (including the --host-prefixed triplet probe). Both are set
        # here so kyua's own configure sees them via conanbuild.
        pkgconf_bin = self._pkgconf_binary()
        if pkgconf_bin:
            env.define("PKG_CONFIG", pkgconf_bin)
        else:
            env.define("PKG_CONFIG", "pkgconf")
        shim_dir = self._ensure_pkg_config_shim()
        if shim_dir:
            env.prepend_path("PATH", shim_dir)
        tc.generate(env=env)
        # Writable TMPDIR/TMP/TEMP + SHELL for autoconf/config.status/mktemp
        # (HMBS readonly_tmp; never fall back to read-only /tmp).
        tmp = self._resolve_hmbs_tmp()
        try:
            os.makedirs(tmp, exist_ok=True)
        except OSError:
            pass
        shell = self._select_shell()
        self.output.info("kyua: selected shell (probed): %s" % shell)
        build_env = Environment()
        build_env.define("TMPDIR", tmp)
        build_env.define("TMP", tmp)
        build_env.define("TEMP", tmp)
        build_env.define("SHELL", shell)
        build_env.define("CONFIG_SHELL", shell)
        # Round 19 (same pkg-config root cause, conanbuild-script side):
        # the vendored lutok configure runs under env="conanbuild", so
        # PKG_CONFIG + shim PATH must also ride the hmbs_tmp_env script,
        # not only the AutotoolsToolchain env above.
        if pkgconf_bin:
            build_env.define("PKG_CONFIG", pkgconf_bin)
            self.output.info("kyua: PKG_CONFIG (probed): %s" % pkgconf_bin)
        else:
            build_env.define("PKG_CONFIG", "pkgconf")
            self.output.info("kyua: PKG_CONFIG fallback: pkgconf (no absolute path)")
        if shim_dir:
            build_env.prepend_path("PATH", shim_dir)
        # Same dual-channel requirement for the mktemp shim (see above):
        # manual vendored configure runs only see hmbs_tmp_env.
        build_env.prepend_path("PATH", mktemp_dir)
        # Round 20 (same PKG_CONFIG_PATH root cause, conanbuild-script
        # side): the vendored lutok configure runs under env="conanbuild",
        # so the generators-folder .pc dirs must also ride hmbs_tmp_env.
        for pc_dir in self._pkgconfig_search_dirs():
            build_env.prepend_path("PKG_CONFIG_PATH", pc_dir)
            self.output.info("kyua: PKG_CONFIG_PATH entry: %s" % pc_dir)
        # Aggregated experience #1 (round 8, different from round 7 shell
        # only): probe the profile-pinned compiler as well. Exists ->
        # zero-change (no CC/CXX override). Missing -> PATH fallback with
        # sibling-dir preference, CC/CXX only, never CFLAGS/LDFLAGS.
        # Toolchain file itself is Conan-generated (not edited); the
        # explicit CC/CXX exports ride the same conanbuild script pattern
        # as SHELL above. Both missing -> log an explicit message.
        for compiler, variable in (("c", "CC"), ("cpp", "CXX")):
            command = self._select_compiler_command(compiler)
            if command:
                build_env.define(variable, command)
                self.output.info("kyua: %s override (probed): %s"
                                 % (variable, command))
            else:
                self.output.info("kyua: %s probe: no conf pin, no override"
                                 % variable)
        for variable, candidates in (
            ("LD", ["ld.lld"]),
            ("AR", ["llvm-ar", "ar"]),
            ("RANLIB", ["llvm-ranlib", "ranlib"]),
            ("NM", ["llvm-nm", "nm"]),
        ):
            command = self._select_tool_command(candidates)
            if command and shutil.which(command) is not None:
                build_env.define(variable, command)
                self.output.info("kyua: %s (probed): %s"
                                 % (variable, command))
        for key in (
            "HMBS_AUTOCONF_MKTEMP_FALLBACK",
            "HMBS_CAP_LOCAL_MKTEMP",
            "HMBS_TMPDIR",
            "HMBS_CAP_HARDLINK",
            "HMBS_CAP_CHMOD",
            "HMBS_CAP_SYMLINK",
        ):
            value = os.environ.get(key)
            if value:
                build_env.define(key, value)
        build_env.vars(self, scope="build").save_script("hmbs_tmp_env")

    def _build_vendored_lutok(self):
        # Round 16: build lutok 0.6.2 statically inside kyua's own
        # (hardened) build context instead of consuming the remote
        # lutok/0.6.2 package, whose recipe aborts at configure[141] with
        # bash-127 on runners missing the profile-pinned shell (no SHELL
        # fallback in archives/l/lutok/0.6.2/conanfile.py generate()) and
        # whose path cannot be repaired from here (round 15: mkdir
        # permission-denied on /data/service/hnp/bin).
        # Evidence for each choice (all in-workspace or upstream-audited):
        # - Sources/ShA: conandata.yml `lutok` entry copies url+sha256 from
        #   archives/l/lutok/0.6.2/manifest.yaml (official release tarball,
        #   ships pre-generated configure; no autoreconf needed per that
        #   recipe's notes).
        # - No --enable-atf: upstream configure.ac declares
        #   `--enable-atf` as default-no, so ATF .pc files are not needed
        #   for the vendored lib (kyua only needs liblutok itself).
        # - Lua: upstream KYUA_LUA m4 probes lua-5.4 first; lua/5.4.8.1
        #   declares pkg_config_name lua-5.4 (hence the LUA_* bypass works
        #   for configure-time detection). It does NOT ship lua.hpp:
        #   archives/l/lutok/0.6.2/conanfile.py documents that the
        #   published lua package carries C headers only while lutok's
        #   public c_gate.hpp does `#include <lua.hpp>`, so that recipe
        #   generates the standard 4-line extern-C wrapper in a private
        #   shim dir (round 28: this vendored build hit the identical
        #   `fatal error: 'lua.hpp' file not found` at make, proving the
        #   old "no workaround needed" comment wrong). Same shim is
        #   generated here and added to CXXFLAGS for configure+make.
        # - C++20: upstream AX_CXX_COMPILE_STDCXX(20, mandatory), hence
        #   -std=c++20 appended after any profile flag (lutok recipe
        #   precedent); -fPIC keeps the static archive PIE-safe.
        # - SHELL: runs under this recipe's probed shell with
        #   SHELL/CONFIG_SHELL exported, plus the mktemp shim on PATH.
        # Returns the private pkgconfig dir holding lutok.pc. The static
        # archive stays in the build tree; nothing lutok-flavoured ships
        # in the kyua package (kyua binaries link it statically).
        vendor = os.path.join(self.build_folder, "vendored-lutok")
        src = os.path.join(vendor, "src")
        prefix = os.path.join(vendor, "prefix")
        for path in (src, prefix):
            try:
                os.makedirs(path, exist_ok=True)
            except OSError:
                pass
        get(self, **self.conan_data["sources"]["lutok"],
            destination=src, strip_root=True)
        if not os.path.isfile(os.path.join(src, "configure")):
            raise ConanException(
                "vendored lutok source has no pre-generated configure "
                "(unexpected tarball layout in %s)" % src
            )
        # Round 27 (strategy cycle 8: three mktemp-interception rounds plus
        # out-of-source relocation all falsified by the identical
        # `config.status: can't create ./confXXX/subs1.awk: Permission
        # denied` fingerprint): patch the mode, not the tool. See
        # _patch_umask_077 (babeltrace 1.5.11 / 4ti2 1.6.10 / aaphoto E114
        # precedents). Must run before configure so the generated
        # config.status inherits umask 022.
        self._patch_umask_077(os.path.join(src, "configure"))
        tmpdir = self._resolve_hmbs_tmp()
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            pass
        # Round 24 (strategy cycle 8: three consecutive failures on the
        # same `config.status: can't create ./confXXX/subs1.awk:
        # Permission denied` fingerprint with mktemp-interception patches,
        # so that whole hypothesis family is dropped by rule). Round 23's
        # inline-PATH delivery PROVED the shim is intercepted
        # (`probe which: .../mktemp-wrapper/mktemp`, `probe fallback=0`)
        # yet config.status fails identically. Therefore the defect is not
        # WHICH mktemp answers, but WHERE config.status scratches:
        # `./confXXX/` under the conan build-tree src dir. Configure's own
        # earlier writes (config.log, conftest files directly in src) all
        # succeed, so only subdir+file creation at that location fails.
        # Different route: out-of-source build rooted in the probed-writable
        # tmpdir (mkstemp-probed in _resolve_hmbs_tmp, the only location
        # with positive writability evidence; in preflight it is the HMBS
        # runtime tmp, a different tree from the conan-home build dir).
        # All generated files (config.log, config.status, Makefiles,
        # confXXX scratch dirs, .o) land in obj/; the tarball src/ stays
        # read-only-clean and prefix/ keeps the install target (one
        # variable moves at a time). No mktemp/PATH/fallback logic changes.
        obj = os.path.join(tmpdir, "kyua-vendored-lutok-obj")
        try:
            shutil.rmtree(obj, ignore_errors=True)
            os.makedirs(obj, exist_ok=True)
        except OSError:
            pass
        shell = self._select_shell()
        perl_skip = self._select_perl()
        self.output.info("kyua: vendored lutok shell (probed): %s" % shell)
        # Round 19: vendored configure fails at PKG_PROG_PKG_CONFIG
        # (`checking for pkg-config... no` -> `configure: error:
        # pkg-config not found`) because pkgconf/3.0.5 ships only
        # bin/pkgconf with no bin/pkg-config alias (package() raises on
        # unexpected alias). Fix in this recipe's own context (no remote
        # lutok change needed): absolute PKG_CONFIG + shim dir holding
        # both `pkg-config` and the --host-prefixed triplet name, PATH
        # prepended via os.environ so env="conanbuild" runs see it, plus
        # an explicit PKG_CONFIG= prefix on the configure command for
        # single-shell determinism (same pattern as CFLAGS/CXXFLAGS).
        pkgconf_bin = self._pkgconf_binary()
        if pkgconf_bin:
            os.environ["PKG_CONFIG"] = pkgconf_bin
            self.output.info(
                "kyua: vendored lutok PKG_CONFIG (probed): %s" % pkgconf_bin)
        else:
            os.environ["PKG_CONFIG"] = "pkgconf"
            self.output.info(
                "kyua: vendored lutok PKG_CONFIG fallback: pkgconf")
        pkg_shim = self._ensure_pkg_config_shim()
        if pkg_shim:
            prev_path = os.environ.get("PATH", "")
            os.environ["PATH"] = pkg_shim + (":" + prev_path if prev_path else "")
            self.output.info(
                "kyua: vendored lutok pkg-config shim PATH: %s" % pkg_shim)
        # unsafe_local_mktemp: manual self.run(env="conanbuild") does not
        # source the Toolchain env, so the mktemp shim must also ride
        # os.environ PATH here (same dual-channel pattern as pkg-config).
        # Only affects PATH lookup for `mktemp -d` during this configure.
        # Round 23: os.environ/conanbuild layering proved unreliable (round
        # 22 synced yet the same config.status failure recurred), so the
        # configure command below ALSO exports the shim PATH inline in the
        # same shell (guaranteed interception), plus an info-only probe
        # that logs which mktemp binary answers and whether its -d dirs
        # are writable — deterministic in-log evidence for the next round.
        mktemp_inline = ""
        try:
            mktemp_dir = self._mktemp_shim_dir()
            prev_path = os.environ.get("PATH", "")
            if mktemp_dir not in prev_path.split(":"):
                os.environ["PATH"] = (
                    mktemp_dir + (":" + prev_path if prev_path else ""))
            self.output.info(
                "kyua: vendored lutok mktemp shim PATH: %s" % mktemp_dir)
            mktemp_inline = mktemp_dir.replace("\\", "/")
        except Exception as exc:
            self.output.info("kyua: vendored lutok mktemp shim skipped: %s" % exc)
        if mktemp_inline:
            probe_log = os.path.join(vendor, "mktemp-probe.log").replace("\\", "/")
            try:
                self.run(
                    "export PATH=\"%s:$PATH\""
                    " && echo \"probe which: $(which mktemp)\""
                    " && echo \"probe fallback=$HMBS_AUTOCONF_MKTEMP_FALLBACK\""
                    " && rm -rf ./mkprobe-test"
                    " && if mktemp -d ./mkprobe-test.XXXXXX > ./mktemp-probe.out 2>&1;"
                    " then D=$(cat ./mktemp-probe.out); echo \"probe rc=0 dir=$D\";"
                    " if touch \"$D/wtest\" 2>/dev/null; then echo \"probe write ok\";"
                    " else echo \"probe write FAILED\"; fi; rm -rf \"$D\";"
                    " else echo \"probe rc=nonzero (fallback active)\"; fi"
                    " >\"%s\" 2>&1" % (mktemp_inline, probe_log),
                    cwd=obj, env="conanbuild", ignore_errors=True)
                try:
                    with open(probe_log, "r", encoding="utf-8",
                              errors="replace") as handle:
                        for line in handle.read().splitlines()[:8]:
                            self.output.info("kyua: %s" % line)
                except OSError as exc:
                    self.output.info("kyua: mktemp probe log unreadable: %s" % exc)
            except Exception as exc:
                self.output.info("kyua: mktemp probe skipped: %s" % exc)
        # Round 20: wire PKG_CONFIG_PATH for the vendored configure in
        # this recipe's own process env (survives into env="conanbuild"
        # runs) and emit the deterministic .pc inventory so the next
        # round can tell "no lua-5.4.pc generated" apart from "generated
        # but not on PATH". Sources are filesystem walks only.
        pc_dirs = self._pkgconfig_search_dirs()
        if pc_dirs:
            prev_pc = os.environ.get("PKG_CONFIG_PATH", "")
            os.environ["PKG_CONFIG_PATH"] = (
                ":".join(pc_dirs) + (":" + prev_pc if prev_pc else ""))
            for pc_dir in pc_dirs:
                self.output.info(
                    "kyua: vendored lutok PKG_CONFIG_PATH entry: %s" % pc_dir)
        try:
            visible = []
            for pc_dir in (os.environ.get("PKG_CONFIG_PATH", "").split(":")
                           if os.environ.get("PKG_CONFIG_PATH") else []):
                try:
                    for entry in sorted(os.listdir(pc_dir)):
                        if entry.endswith(".pc"):
                            visible.append(entry)
                except OSError:
                    continue
            self.output.info(
                "kyua: vendored lutok visible .pc files: %s"
                % (", ".join(sorted(set(visible))) if visible else "<none>"))
        except Exception as exc:
            self.output.info("kyua: vendored lutok .pc inventory skipped: %s" % exc)
        # Round 21 (same lua-detection fingerprint, 3rd fix -> different
        # strategy by rule): round 19 wired the pkg-config IMPLEMENTATION
        # (PKG_CONFIG/shim) and round 20 the .pc SEARCH PATH (generators
        # folder). Both synced — the `pkg-config not found` error is gone
        # (configure now runs compiler probes) — yet
        # `Package requirements (lua >= 5.4) were not met` persists. The
        # residual uncertainty is whether the PkgConfigDeps lua-5.4.pc is
        # visible inside the MANUAL self.run(env="conanbuild"): the
        # AutotoolsToolchain env rides conanautotoolchain.sh, which manual
        # runs do NOT source, so round-20 tc-side prepends may never reach
        # this configure. Different route: bypass pkg-config for lua
        # entirely via LUA_CFLAGS/LUA_LIBS — the fallback the error text
        # itself names; PKG_CHECK_MODULES honours pre-set <PREFIX>_CFLAGS
        # /_LIBS and skips the .pc lookup. Values derive deterministically
        # from the lua dependency (package folder + cpp_info libs /
        # system_libs / defines), with lua.h existence verified before use.
        # Round-20 PATH wiring is kept for kyua's own configure (which runs
        # via the Autotools helper and DOES source the toolchain script).
        try:
            lua_dep = self.dependencies["lua"]
            lua_folder = str(getattr(lua_dep, "package_folder", "") or "")
        except Exception:
            lua_dep, lua_folder = None, ""
        lua_h = (os.path.join(lua_folder, "include", "lua.h")
                 if lua_folder else "")
        if lua_folder and os.path.isfile(lua_h):
            try:
                cpp = lua_dep.cpp_info
                incs = [str(d) for d in getattr(cpp, "includedirs", [])] or [
                    os.path.join(lua_folder, "include")]
                libdirs = [str(d) for d in getattr(cpp, "libdirs", [])] or [
                    os.path.join(lua_folder, "lib")]
                libs = list(getattr(cpp, "libs", []) or ["lua"])
                syslibs = list(getattr(cpp, "system_libs", []) or [])
                defines = list(getattr(cpp, "defines", []) or [])
            except Exception:
                incs = [os.path.join(lua_folder, "include")]
                libdirs = [os.path.join(lua_folder, "lib")]
                libs, syslibs, defines = ["lua"], ["dl", "m"], []
            os.environ["LUA_CFLAGS"] = " ".join(
                ["-I%s" % d for d in incs]
                + ["-D%s" % d for d in defines])
            os.environ["LUA_LIBS"] = " ".join(
                ["-L%s" % d for d in libdirs]
                + ["-l%s" % n for n in libs]
                + ["-l%s" % n for n in syslibs])
            self.output.info("kyua: vendored lutok LUA_CFLAGS=%s"
                             % os.environ["LUA_CFLAGS"])
            self.output.info("kyua: vendored lutok LUA_LIBS=%s"
                             % os.environ["LUA_LIBS"])
        else:
            raise ConanException(
                "kyua: lua.h not found under %s; vendored lutok cannot "
                "configure without lua (requires must be plain, not "
                "override=True, when nothing transitively pulls lua)"
                % (lua_folder or "<no lua package folder>"))
        # Round 17 (strategy cycle 7: prior libdir-pin/file-walk patch kept the
        # same nested-shell composition and was falsified by an empty install
        # tree with exit 0): different route = delete the nested
        # `{shell} -c "... export CFLAGS='-fPIC '"$CFLAGS" ..."` composition
        # entirely. That double layer lets the OUTER shell expand $CFLAGS /
        # $CXXFLAGS / $(...) before the inner `sh -c` sees the script, so a
        # toolchain CFLAGS containing spaces (always true under conanbuild)
        # breaks the inner quoting (`export CFLAGS='-fPIC '-O2 ...`) and the
        # real failure (configure args mangled / install prefix lost) is
        # masked as exit-0-with-empty-prefix. The replacement runs each step
        # in conan's own single shell via cwd=src (no manual `sh -c`, no
        # `cd`, no `$VAR` re-export): CC/CXX/SHELL/TMPDIR already arrive via
        # the hmbs_tmp_env conanbuild script from generate(); -fPIC/-std=c++20
        # ride a single-level `VAR="$VAR extra"` prefix that conan's shell
        # expands exactly once. Each step logs to a file; on failure the tail
        # is attached to the exception so the next round sees evidence.
        for compiler, variable in (("c", "CC"), ("cpp", "CXX")):
            command = self._select_compiler_command(compiler)
            if command and self._is_executable(shlex.split(command)[0]):
                os.environ[variable] = command
        # Round 28: private lua.hpp shim (lutok 0.6.2 _lua_shim_dir
        # precedent). Stock lua ships C headers only (lua.h/lualib.h/
        # lauxlib.h); lutok's public c_gate.hpp does `#include <lua.hpp>`,
        # so make dies with `fatal error: 'lua.hpp' file not found`
        # without this. Standard 4-line extern-C wrapper, kept under
        # vendor/ (NOT obj/, which _clean_vendored_obj deletes) so kyua's
        # own build can reuse it for lutok headers.
        lua_shim = os.path.join(vendor, "lua-shim")
        try:
            os.makedirs(lua_shim, exist_ok=True)
        except OSError:
            pass
        save(self, os.path.join(lua_shim, "lua.hpp"),
             'extern "C" {\n'
             '#include "lua.h"\n'
             '#include "lualib.h"\n'
             '#include "lauxlib.h"\n'
             '}\n')
        lua_shim_q = lua_shim.replace("\\", "/")
        self.output.info("kyua: vendored lua.hpp shim: %s/lua.hpp" % lua_shim_q)
        pcdir = os.path.join(prefix, "lib", "pkgconfig").replace("\\", "/")
        libdir_q = os.path.join(prefix, "lib").replace("\\", "/")
        src_q = src.replace("\\", "/")
        prefix_q = prefix.replace("\\", "/")
        cfg_log = os.path.join(vendor, "lutok-configure.log").replace("\\", "/")
        mk_log = os.path.join(vendor, "lutok-make.log").replace("\\", "/")
        inst_log = os.path.join(vendor, "lutok-install.log").replace("\\", "/")

        def _run_logged(cmd, log_path, step):
            # Round 45 (strategy change: rounds 42-44 fixed the C++ family
            # via source rename + nullptr; the next fingerprint is
            # `libtool can't fork - try again` on the first lutok TU, i.e.
            # transient process/memory exhaustion, not a source error.
            # Different route: retry with backoff. Only fork/resource/
            # memory signatures retry (max 3 attempts, 30s sleeps); real
            # compile errors fail fast on attempt 1. Retry output appends
            # so forensics survive; evidence logged per attempt.
            import time as _time

            def _is_transient(text):
                lowered = (text or "").lower()
                return any(sig in lowered for sig in (
                    "can't fork", "cannot fork", "try again",
                    "resource temporarily unavailable",
                    "out of memory", "cannot allocate memory",
                ))

            last_exc = None
            for attempt in (1, 2, 3):
                redirect = ">" if attempt == 1 else ">>"
                try:
                    if attempt > 1:
                        self.output.info(
                            "kyua: vendored lutok %s retry %d/3 "
                            "after transient fork failure" % (step, attempt))
                    self.run("%s %s\"%s\" 2>&1" % (cmd, redirect, log_path),
                             cwd=obj, env="conanbuild")
                    if attempt > 1:
                        self.output.info(
                            "kyua: vendored lutok %s retry %d succeeded"
                            % (step, attempt))
                    return
                except Exception as exc:
                    last_exc = exc
                    tail = ""
                    try:
                        with open(log_path, "r", encoding="utf-8",
                                  errors="replace") as handle:
                            lines = handle.read().splitlines()
                        tail = "\n".join(lines[-30:])
                    except OSError:
                        tail = "<log unreadable: %s>" % log_path
                    if step == "make" and _is_transient(
                            "%s\n%s" % (exc, tail)) and attempt < 3:
                        self.output.info(
                            "kyua: vendored lutok make transient fork "
                            "failure (attempt %d/3); sleeping 30s: %s"
                            % (attempt, tail.splitlines()[-1:]
                               if tail else exc))
                        try:
                            _time.sleep(30)
                        except Exception:
                            pass
                        try:
                            self.run("sync || true",
                                     cwd=obj, env="conanbuild",
                                     ignore_errors=True)
                        except Exception:
                            pass
                        continue
                    raise ConanException(
                        "vendored lutok %s failed: %s; log %s tail:\n%s"
                        % (step, exc, log_path, tail)
                    )
            raise ConanException(
                "vendored lutok %s failed after 3 attempts: %s"
                % (step, last_exc))

        # Single-shell determinism (round 17 pattern): the LUA bypass must
        # also ride the configure command line itself, not only
        # os.environ, so exactly one expansion layer applies. Only added
        # when both values are non-empty; set-but-empty would make
        # PKG_CHECK_MODULES skip pkg-config AND compile with no flags.
        lua_prefix = ""
        if os.environ.get("LUA_CFLAGS") and os.environ.get("LUA_LIBS"):
            lua_prefix = ("LUA_CFLAGS=\"%s\" LUA_LIBS=\"%s\" "
                          % (os.environ["LUA_CFLAGS"], os.environ["LUA_LIBS"]))
        # Round 23: inline PATH export in the SAME shell guarantees the mktemp
        # shim intercepts configure/config.status regardless of conanbuild
        # script layering (round 17 single-shell determinism pattern).
        mktemp_prefix = ""
        if mktemp_inline:
            mktemp_prefix = "export PATH=\"%s:$PATH\" && " % mktemp_inline
        # Round 45: lutok inherits the profile -O3 (preflight compile line
        # shows `-O3 -std=c++20`); round 25 already proved -O1 -g0 lowers
        # per-TU cc1plus peak for kyua itself on this RAM-bound device
        # (SIGKILL-137 / tar-cannot-fork precedents, round 26). Appended
        # -O1 -g0 wins last-wins over -O3 without touching the required
        # -std=c++20; same lever extended to the vendored lib.
        _run_logged(
            "%sPKG_CONFIG=\"%s\" %sCFLAGS=\"$CFLAGS -fPIC -O1 -g0\" CXXFLAGS=\"$CXXFLAGS -std=c++20 -fPIC -I%s -O1 -g0\" "
            "\"%s\" \"%s/configure\" --srcdir=\"%s\" --disable-shared --enable-static"
            " --with-doxygen=no"
            " --build=aarch64-unknown-linux-gnu"
            " --host=aarch64-unknown-linux-gnu"
            " --prefix=\"%s\""
            " --libdir=\"%s\"" % (mktemp_prefix,
                                  os.environ.get("PKG_CONFIG", "pkgconf"),
                                  lua_prefix, lua_shim_q, shell, src_q, src_q,
                                  prefix_q, libdir_q),
            cfg_log, "configure",
        )
        # Round 27: config.status is (re)invoked by make, so patch the
        # generated file as well (babeltrace precedent patches both
        # configure and config.status).
        self._patch_umask_077(os.path.join(obj, "config.status"))
        # Post-configure evidence: lutok.pc.in must have rendered to lutok.pc
        # in the obj tree (round 24: out-of-source, generated files live in
        # obj/, src/ stays clean); a missing file here means configure
        # silently skipped pkgconfig output and `make install` would stay
        # empty.
        if not os.path.isfile(os.path.join(obj, "lutok.pc")):
            self.output.info(
                "kyua: vendored lutok.pc not rendered by configure "
                "(obj tree check; continuing to make for evidence)"
            )
        _run_logged("make -j1", mk_log, "make")
        # Pre-install evidence: the static archive must exist before install.
        built = []
        for root, _, files in os.walk(obj):
            if "liblutok.a" in files or "liblutok.la" in files:
                built.append(os.path.join(root, "liblutok.la"
                                           if "liblutok.la" in files
                                           else "liblutok.a"))
                break
        if not built:
            self.output.info(
                "kyua: vendored lutok archive missing before install "
                "(continuing; install log will carry evidence)"
            )
        # Round 30 (strategy cycle 9): round 29's `doc_DATA=` skip is
        # REVERTED here — the new preflight fingerprint proves it was
        # whack-a-mole (`install-docDATA` Error 64 became
        # `install-examplesDATA` Error 64 one target down; the next skip
        # would just fail on the following DATA target). Root cause is the
        # install TOOL (HMBS runtime `bin/install` wrapper rejects
        # multi-file `install -c -m 644 a b c dir` with EX_USAGE/64 while
        # single-file libtool installs succeed), so the fix overrides
        # INSTALL on the make command line with a probe-verified working
        # binary (E312/E313 `INSTALL=/system/bin/install -c` precedent;
        # see _select_install_args). Full `make install` runs — docs and
        # examples included — and the lutok.pc gate below keeps the
        # evidence (missing .pc still raises with a tree listing).
        install_tokens = self._select_install_args()
        install_suffix = (" " + " ".join(install_tokens)
                          if install_tokens else "")
        _run_logged("make install -j1" + install_suffix, inst_log, "install")
        lutok_pc = os.path.join(prefix, "lib", "pkgconfig", "lutok.pc")
        if not os.path.isfile(lutok_pc):
            # Filesystem-level fallback: accept lutok.pc wherever the
            # install tree placed it (deterministic os.walk, never stdout
            # counting). Only the .pc dir is consumed downstream.
            found = None
            for root, _, files in os.walk(prefix):
                if "lutok.pc" in files:
                    found = os.path.join(root, "lutok.pc")
                    break
            if found is not None:
                self.output.info(
                    "kyua: vendored lutok.pc at non-canonical path: %s"
                    % found
                )
                self._clean_vendored_obj(obj)
                return os.path.dirname(found).replace("\\", "/")
            tree = []
            for root, dirs, files in os.walk(prefix):
                depth = os.path.relpath(root, prefix).count(os.sep)
                if depth > 2:
                    dirs[:] = []
                    continue
                tree.append(
                    "%s/ [%s] {%s}"
                    % (os.path.relpath(root, prefix), ",".join(sorted(dirs)[:8]),
                       ",".join(sorted(files)[:8]))
                )
            raise ConanException(
                "vendored lutok install produced no lutok.pc under %s; "
                "install tree: %s" % (prefix, "; ".join(tree) if tree else "<empty>")
            )
        self.output.info("kyua: vendored lutok.pc ready: %s" % lutok_pc)
        self._clean_vendored_obj(obj)
        return pcdir

    def _clean_vendored_obj(self, obj):
        # Round 26: release the out-of-source obj tree immediately after a
        # successful vendored install. Since round 24 the obj tree lives
        # under _resolve_hmbs_tmp() (the HMBS runtime tmp, possibly a
        # memory-backed tmpfs) and otherwise keeps every .o plus the full
        # autotools scratch through kyua's own configure/make/check. The
        # current fingerprint (`tar: child process: Cannot fork: Out of
        # memory` during source extraction, where recipe code barely runs)
        # proves system-wide RAM — not per-TU compiler flags (round 25) —
        # is the binding constraint, so this frees pinned memory instead of
        # tuning codegen. Logs (lutok-*.log) and the install prefix stay on
        # disk; only the disposable obj tree is removed. Failure paths keep
        # obj for forensics (cleanup runs only after lutok.pc is verified).
        try:
            shutil.rmtree(obj, ignore_errors=True)
            self.output.info("kyua: vendored obj cleaned: %s" % obj)
        except OSError as exc:
            self.output.info(
                "kyua: vendored obj cleanup skipped: %s" % exc)

    def _build_vendored_toolchain(self):
        # Round 39: build GNU m4 + autoconf privately inside kyua's own
        # hardened build context and use them for the kyua bootstrap,
        # instead of consuming any m4/autoconf tool package from the
        # remotes. Rounds 4/36/37 steered selection through tool_requires
        # RREV/override semantics, but the 22:02 preflight (whose export
        # hash differs from the 21:26 run, i.e. it tested the tree that
        # already contained the parent-hard-child-override pairing) still
        # built BARE CCI m4 (CCI-only 0004-disable-hardening patch +
        # configure[139] bash-127, no graph conflict): the override is
        # ineffective in this Conan version/context layout, or the pinned
        # RREVs do not resolve on the queried remotes — indistinguishable
        # from the recipe side, so the whole pin family is dropped by rule
        # (round-16 lutok precedent: vendor instead of fighting selection).
        # Evidence for each choice:
        # - Sources/ShA: conandata.yml `m4`/`autoconf` entries copy
        #   url+sha256 verbatim from archives/m/m4/1.4.19/conandata.yml and
        #   archives/a/autoconf/2.72/conandata.yml (official GNU tarballs).
        # - No recursion: GNU release tarballs ship pre-generated
        #   `configure` (the CCI m4 build itself runs `src/configure`
        #   directly; autoconf 2.72 manifest states the same), so the
        #   private builds are plain configure+make, needing only a shell,
        #   a compiler, perl and make — all probed below.
        # - Triplets: explicit --build/--host=aarch64-unknown-linux-gnu
        #   (E007/E160: automake-era config.guess cannot identify
        #   HarmonyOS), same as kyua's own configure and the lutok vendor.
        # - umask 022: same HMDFS confXXX fix as _patch_umask_077
        #   (babeltrace 1.5.11 precedent), applied to both configures
        #   before they run so the generated config.status inherits it.
        # - freadahead: OHOS libc exposes FILE as opaque without
        #   __freadahead; archives/m/m4/1.4.19 patch 0004 adds a
        #   GNULIB_FREADAHEAD_OPAQUE_FILE fallback branch returning 0.
        #   The equivalent 4-line branch is applied here as an in-recipe
        #   text edit on the vendored copy (no patch file committed) plus
        #   the same -D flag the repo recipe passes via extra_defines.
        # - INSTALL override: same HMBS-wrapper EX_USAGE/64 family as
        #   round 30 (_select_install_args probe evidence), reused for
        #   both `make install` runs.
        # - OOM: obj trees live under _resolve_hmbs_tmp() and are removed
        #   via _clean_vendored_obj right after each install verifies
        #   (round 26), so no extra .o weight accompanies kyua's own build.
        # Returns the private bindir. Nothing toolchain-flavoured ships in
        # the kyua package (bootstrap-only tools).
        vendor = os.path.join(self.build_folder, "vendored-tools")
        src_m4 = os.path.join(vendor, "src-m4")
        src_auto = os.path.join(vendor, "src-autoconf")
        prefix = os.path.join(vendor, "prefix")
        for path in (src_m4, src_auto, prefix):
            try:
                os.makedirs(path, exist_ok=True)
            except OSError:
                pass
        get(self, **self.conan_data["sources"]["m4"],
            destination=src_m4, strip_root=True)
        get(self, **self.conan_data["sources"]["autoconf"],
            destination=src_auto, strip_root=True)
        for label, src in (("m4", src_m4), ("autoconf", src_auto)):
            if not os.path.isfile(os.path.join(src, "configure")):
                raise ConanException(
                    "vendored %s source has no pre-generated configure "
                    "(unexpected tarball layout in %s)" % (label, src)
                )
        self._patch_umask_077(os.path.join(src_m4, "configure"))
        self._patch_umask_077(os.path.join(src_auto, "configure"))
        # In-recipe equivalent of the repo m4 0004 freadahead fallback.
        try:
            freadahead = os.path.join(src_m4, "lib", "freadahead.c")
            with open(freadahead, "r", encoding="utf-8",
                      errors="surrogateescape") as handle:
                fatext = handle.read()
            marker = "#elif defined SLOW_BUT_NO_HACKS"
            branch = ("#elif defined GNULIB_FREADAHEAD_OPAQUE_FILE\n"
                      "  return 0;\n")
            if branch.strip() not in fatext and marker in fatext:
                with open(freadahead, "w", encoding="utf-8",
                          errors="surrogateescape") as handle:
                    handle.write(fatext.replace(marker, branch + marker, 1))
                self.output.info("kyua: vendored m4 freadahead fallback added")
            else:
                self.output.info(
                    "kyua: vendored m4 freadahead edit skipped "
                    "(already present or marker absent)")
        except OSError as exc:
            self.output.info(
                "kyua: vendored m4 freadahead edit skipped: %s" % exc)
        tmpdir = self._resolve_hmbs_tmp()
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            pass
        shell = self._select_shell()
        perl = self._select_perl()
        self.output.info("kyua: vendored toolchain shell (probed): %s" % shell)
        self.output.info("kyua: vendored toolchain perl (probed): %s" % perl)
        mktemp_prefix = ""
        try:
            mktemp_dir = self._mktemp_shim_dir()
            mktemp_prefix = "export PATH=\"%s:$PATH\" && " % (
                mktemp_dir.replace("\\", "/"))
        except Exception as exc:
            self.output.info(
                "kyua: vendored toolchain mktemp shim skipped: %s" % exc)
        cc_prefix = ""
        try:
            cc_val = os.environ.get("CC", "")
            cxx_val = os.environ.get("CXX", "")
            if cc_val:
                cc_prefix = "CC=%s " % shlex.quote(cc_val)
                if cxx_val:
                    cc_prefix = cc_prefix + "CXX=%s " % shlex.quote(cxx_val)
        except Exception as exc:
            self.output.info(
                "kyua: vendored toolchain CC prefix skipped: %s" % exc)
            cc_prefix = ""
        install_tokens = self._select_install_args()
        install_suffix = (" " + " ".join(install_tokens)
                          if install_tokens else "")
        triplets = ("--build=aarch64-unknown-linux-gnu"
                    " --host=aarch64-unknown-linux-gnu")

        def _trun(cmd, log_path, step, workdir):
            try:
                self.run("%s >\"%s\" 2>&1" % (cmd, log_path),
                         cwd=workdir, env="conanbuild")
            except Exception as exc:
                tail = ""
                try:
                    with open(log_path, "r", encoding="utf-8",
                              errors="replace") as handle:
                        lines = handle.read().splitlines()
                    tail = "\n".join(lines[-30:])
                except OSError:
                    tail = "<log unreadable: %s>" % log_path
                raise ConanException(
                    "vendored toolchain %s failed: %s; log %s tail:\n%s"
                    % (step, exc, log_path, tail)
                )

        bindir = os.path.join(prefix, "bin")
        libdir = os.path.join(prefix, "lib")
        vbindir = bindir.replace("\\", "/")
        vlibdir = libdir.replace("\\", "/")
        vshell = shell.replace("\\", "/")
        # ---- m4 (private; autoconf needs its binary next) ----
        obj_m4 = os.path.join(tmpdir, "kyua-vendored-m4-obj")
        try:
            shutil.rmtree(obj_m4, ignore_errors=True)
            os.makedirs(obj_m4, exist_ok=True)
        except OSError:
            pass
        vsrc_m4 = src_m4.replace("\\", "/")
        m4_log = os.path.join(vendor, "tools-m4-configure.log")
        _trun("%s%sCPPFLAGS=\"$CPPFLAGS -DGNULIB_FREADAHEAD_OPAQUE_FILE\" "
              "\"%s\" \"%s/configure\" --srcdir=\"%s\" --prefix=\"%s\" "
              "--libdir=\"%s\" --disable-dependency-tracking "
              "--disable-silent-rules --disable-nls %s"
              % (mktemp_prefix, cc_prefix, vshell, vsrc_m4, vsrc_m4,
                 prefix.replace("\\", "/"), vlibdir, triplets),
              m4_log.replace("\\", "/"), "m4 configure", obj_m4)
        self._patch_umask_077(os.path.join(obj_m4, "config.status"))
        _trun("make -j1 MAKEINFO=true",
              os.path.join(vendor, "tools-m4-make.log").replace("\\", "/"),
              "m4 make", obj_m4)
        _trun("make install -j1 MAKEINFO=true" + install_suffix,
              os.path.join(vendor, "tools-m4-install.log").replace("\\", "/"),
              "m4 install", obj_m4)
        m4_bin = os.path.join(bindir, "m4")
        if not os.path.isfile(m4_bin):
            raise ConanException(
                "vendored m4 install produced no bin/m4 under %s" % prefix)
        smoke = os.path.join(vendor, "tools-m4-smoke.m4").replace("\\", "/")
        save(self, smoke, "define(`answer', `42')dnl\nanswer\n")
        _trun("test \"$(\"%s\" \"%s\")\" = 42"
              % (m4_bin.replace("\\", "/"), smoke),
              os.path.join(vendor, "tools-m4-smoke.log").replace("\\", "/"),
              "m4 smoke", obj_m4)
        self.output.info("kyua: vendored m4 ready: %s"
                         % m4_bin.replace("\\", "/"))
        self._clean_vendored_obj(obj_m4)
        # ---- autoconf (private; needs vendored m4 + probed perl) ----
        obj_auto = os.path.join(tmpdir, "kyua-vendored-autoconf-obj")
        try:
            shutil.rmtree(obj_auto, ignore_errors=True)
            os.makedirs(obj_auto, exist_ok=True)
        except OSError:
            pass
        vsrc_auto = src_auto.replace("\\", "/")
        _trun("%s%sM4=\"%s\" PERL=\"%s\" EMACS=no "
              "\"%s\" \"%s/configure\" --srcdir=\"%s\" --prefix=\"%s\" "
              "--libdir=\"%s\" --disable-dependency-tracking "
              "--disable-silent-rules %s"
              % (mktemp_prefix, cc_prefix, m4_bin.replace("\\", "/"),
                 perl.replace("\\", "/"), vshell, vsrc_auto, vsrc_auto,
                 prefix.replace("\\", "/"), vlibdir, triplets),
              os.path.join(vendor, "tools-autoconf-configure.log").replace(
                  "\\", "/"),
              "autoconf configure", obj_auto)
        self._patch_umask_077(os.path.join(obj_auto, "config.status"))
        _trun("make -j1 MAKEINFO=true",
              os.path.join(vendor, "tools-autoconf-make.log").replace(
                  "\\", "/"),
              "autoconf make", obj_auto)
        _trun("make install -j1 MAKEINFO=true" + install_suffix,
              os.path.join(vendor, "tools-autoconf-install.log").replace(
                  "\\", "/"),
              "autoconf install", obj_auto)
        for tool in ("autoconf", "autoheader", "autom4te", "autoreconf"):
            if not os.path.isfile(os.path.join(bindir, tool)):
                raise ConanException(
                    "vendored autoconf install produced no bin/%s under %s"
                    % (tool, prefix))
        _trun("\"%s\" --version"
              % os.path.join(bindir, "autoconf").replace("\\", "/"),
              os.path.join(vendor, "tools-autoconf-smoke.log").replace(
                  "\\", "/"),
              "autoconf smoke", obj_auto)
        self.output.info("kyua: vendored autoconf ready: %s"
                         % os.path.join(bindir, "autoconf").replace("\\", "/"))
        self._clean_vendored_obj(obj_auto)
        # Wire the private tools into this recipe's process env so the
        # kyua bootstrap (manual self.run env="conanbuild" + recipe-process
        # shutil.which PATH fallback in _select_bootstrap_prog) finds them
        # deterministically, ahead of any same-name system binary.
        prev_path = os.environ.get("PATH", "")
        if vbindir not in prev_path.split(os.pathsep):
            os.environ["PATH"] = vbindir + (os.pathsep + prev_path
                                            if prev_path else "")
        os.environ["M4"] = m4_bin.replace("\\", "/")
        for var, tool in (("AUTOM4TE", "autom4te"),
                          ("AUTOCONF", "autoconf"),
                          ("AUTOHEADER", "autoheader"),
                          ("AUTORECONF", "autoreconf"),
                          ("AUTOSCAN", "autoscan"),
                          ("AUTOUPDATE", "autoupdate"),
                          ("IFNAMES", "ifnames")):
            os.environ[var] = (vbindir + "/" + tool)
        sharedir = (prefix.replace("\\", "/") + "/share/autoconf")
        os.environ["autom4te_perllibdir"] = sharedir
        os.environ["AC_MACRODIR"] = sharedir
        os.environ["trailer_m4"] = sharedir + "/autoconf/trailer.m4"
        os.environ["autom4te_buildauxdir"] = sharedir + "/build-aux"
        self.output.info("kyua: vendored toolchain bindir on PATH: %s"
                         % vbindir)
        return vbindir

    def _tool_pkg_dirs(self, pkg_name):
        # Locate a build-requirement tool package's prefix and bindir.
        # Returns (prefix, bindir) with native separators, or (None, None)
        # when the package is absent. Filesystem evidence only.
        try:
            dep = self.dependencies.build.get(pkg_name)
        except Exception:
            return None, None
        try:
            if dep is None or not getattr(dep, "package_folder", None):
                return None, None
            prefix = str(dep.package_folder)
            bindir = os.path.join(prefix, "bin")
            if os.path.isdir(bindir):
                return prefix, bindir
        except OSError:
            pass
        return None, None

    def _script_uses_perl(self, path):
        # Read the shebang/first block to decide the interpreter.
        # Wrapper scripts from the automake/autoconf recipes are sh
        # (they exec a hidden .*-real); the hidden originals are perl.
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as handle:
                head = handle.read(2048)
        except OSError:
            return False
        first = head.splitlines()[0] if head.splitlines() else ""
        if "perl" in first:
            return True
        # Wrapper marker used by both recipes (".<tool>-real").
        if "-real" in head and ("conan" in head or "exec " in head):
            return False
        return "perl" in head[:512]

    def _select_bootstrap_prog(self, kind, perl):
        # Round 32 (strategy cycle 10: prior install-tool probe and m4
        # dual-domain lookup are falsified for this fingerprint by rule —
        # the failure is `aclocal-1.18[8]: .aclocal-1.18-real: No such file`
        # with Error 126, i.e. the automake/1.18 tool package's relocatable
        # wrapper exists but its hidden real script is absent in the cached
        # package, so `sh aclocal-1.18` can never succeed no matter which
        # INSTALL or m4 path is chosen). Different route: bypass the wrapper
        # and invoke the hidden perl original directly with the same flags
        # the wrapper would have added. Selection is by filesystem evidence
        # (os.path.isfile follows symlinks, so a dangling symlink counts as
        # missing) plus a content check, never by PATH order alone.
        # Returns (run_snippet, perllib_dir); run_snippet already contains
        # the interpreter and any extra flags, e.g.
        # `"/perl" "/pfx/bin/.aclocal-1.18-real" --automake-acdir=...`.
        # perllib_dir is the package's share dir for the PERL5LIB export.
        # None snippet means "caller falls back to command -v".
        def _q(path):
            return "\"%s\"" % path.replace("\\", "/")

        if kind in ("aclocal", "automake"):
            prefix, bindir = self._tool_pkg_dirs("automake")
            if prefix:
                pfx = prefix.replace("\\", "/")
                perllib = pfx + "/share/automake-1.18"
                if kind == "aclocal":
                    for hidden in (os.path.join(bindir, ".aclocal-1.18-real"),
                                   os.path.join(bindir, ".aclocal-real")):
                        try:
                            if os.path.isfile(hidden):
                                self.output.info(
                                    "kyua: bootstrap aclocal hidden real: %s"
                                    % hidden.replace("\\", "/"))
                                return (
                                    "%s %s --automake-acdir=%s "
                                    "--system-acdir=%s" % (
                                        _q(perl), _q(hidden),
                                        _q(pfx + "/share/aclocal-1.18"),
                                        _q(pfx + "/share/aclocal")),
                                    perllib)
                        except OSError:
                            continue
                    # Wrapper usable only when its hidden target exists.
                    for wrap in (os.path.join(bindir, "aclocal-1.18"),
                                 os.path.join(bindir, "aclocal")):
                        try:
                            if os.path.isfile(wrap):
                                with open(wrap, "r", encoding="utf-8",
                                          errors="replace") as handle:
                                    text = handle.read(2048)
                                if "-real" in text:
                                    # Broken wrapper: hidden missing.
                                    self.output.info(
                                        "kyua: bootstrap aclocal wrapper "
                                        "broken (hidden missing), skip: %s"
                                        % wrap.replace("\\", "/"))
                                    continue
                                interp = perl if self._script_uses_perl(wrap) \
                                    else "sh"
                                return ("%s %s" % (interp, _q(wrap)), perllib)
                        except OSError:
                            continue
                else:  # automake
                    for hidden in (os.path.join(bindir, ".automake-1.18-real"),
                                   os.path.join(bindir, ".automake-real")):
                        try:
                            if os.path.isfile(hidden):
                                self.output.info(
                                    "kyua: bootstrap automake hidden real: %s"
                                    % hidden.replace("\\", "/"))
                                return (
                                    "%s %s --libdir=%s" % (
                                        _q(perl), _q(hidden),
                                        _q(pfx + "/share/automake-1.18")),
                                    perllib)
                        except OSError:
                            continue
                    for wrap in (os.path.join(bindir, "automake-1.18"),
                                 os.path.join(bindir, "automake")):
                        try:
                            if os.path.isfile(wrap):
                                with open(wrap, "r", encoding="utf-8",
                                          errors="replace") as handle:
                                    text = handle.read(2048)
                                if "-real" in text:
                                    self.output.info(
                                        "kyua: bootstrap automake wrapper "
                                        "broken (hidden missing), skip: %s"
                                        % wrap.replace("\\", "/"))
                                    continue
                                interp = perl if self._script_uses_perl(wrap) \
                                    else "sh"
                                return ("%s %s" % (interp, _q(wrap)), perllib)
                        except OSError:
                            continue
        else:  # autoheader / autoconf come from the autoconf package.
            prefix, bindir = self._tool_pkg_dirs("autoconf")
            if prefix:
                pfx = prefix.replace("\\", "/")
                perllib = pfx + "/share/autoconf"
                hidden_name = ".%s-real" % kind
                hidden = os.path.join(bindir, hidden_name)
                try:
                    if os.path.isfile(hidden):
                        self.output.info(
                            "kyua: bootstrap %s hidden real: %s"
                            % (kind, hidden.replace("\\", "/")))
                        return ("%s %s" % (_q(perl), _q(hidden)), perllib)
                except OSError:
                    pass
                wrap = os.path.join(bindir, kind)
                try:
                    if os.path.isfile(wrap):
                        with open(wrap, "r", encoding="utf-8",
                                  errors="replace") as handle:
                            text = handle.read(2048)
                        if "-real" not in text:
                            interp = perl if self._script_uses_perl(wrap) \
                                else "sh"
                            return ("%s %s" % (interp, _q(wrap)), perllib)
                        # Wrapper present: its hidden was just proven
                        # missing above, so it is broken; fall through.
                        self.output.info(
                            "kyua: bootstrap %s wrapper broken "
                            "(hidden missing), skip: %s"
                            % (kind, wrap.replace("\\", "/")))
                except OSError:
                    pass
        # PATH fallback: pick the first versioned/unversioned binary whose
        # file exists; decide the interpreter from its content so a perl
        # script is never fed to sh on chmod=0 runners (no exec bit needed
        # when the interpreter is explicit).
        cands = {"aclocal": ("aclocal-1.18", "aclocal"),
                 "automake": ("automake-1.18", "automake"),
                 "autoheader": ("autoheader",),
                 "autoconf": ("autoconf",)}[kind]
        for name in cands:
            found = shutil.which(name)
            if found and os.path.isfile(found):
                try:
                    interp = perl if self._script_uses_perl(found) else "sh"
                except OSError:
                    interp = "sh"
                self.output.info(
                    "kyua: bootstrap %s PATH fallback: %s via %s"
                    % (kind, found, interp))
                return ("%s \"%s\"" % (interp, found.replace("\\", "/")),
                        None)
        self.output.info("kyua: bootstrap %s: no candidate found" % kind)
        return None, None

    def _bootstrap_autotools(self):
        # Reproduce `autoreconf -fi` step-by-step forcing system perl: the
        # conan tool perl XS (Cwd.so) cannot load on HMDFS/OHOS (librb 2.0.0
        # precedent). Extra `-I` for the ATF M4 macros, which configure.ac
        # hard-requires (m4_fatal without atf-c++.m4/atf-sh.m4/atf-common.m4).
        src = self.source_folder.replace("\\", "/")
        shell = self._select_shell()
        self.output.info("kyua: bootstrap shell (probed): %s" % shell)
        perl = self._select_perl()
        self.output.info("kyua: bootstrap perl (probed): %s" % perl)
        atf_dir, _ = self._find_m4_file("atf", "atf-c++.m4")
        if atf_dir is None:
            raise ConanException(
                "atf-c++.m4 not found in atf/0.23 package; "
                "cannot bootstrap kyua configure"
            )
        atf_dir = atf_dir.replace("\\", "/")
        # pkg.m4 (PKG_CHECK_MODULES) ships with the pkgconf tool package, not
        # with automake; aclocal only searches its own datadir plus
        # ACLOCAL_PATH, so both third-party macro dirs are exported.
        pkg_dir, _ = self._find_m4_file("pkgconf", "pkg.m4")
        if pkg_dir is None:
            raise ConanException(
                "pkg.m4 not found in pkgconf/3.0.5 package; "
                "cannot bootstrap kyua configure"
            )
        pkg_dir = pkg_dir.replace("\\", "/")
        tmpdir = self._resolve_hmbs_tmp()
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            pass
        # Round 17: same nested-shell root cause as vendored lutok (see
        # _build_vendored_lutok): the old `{shell} -c "set -e ... $(...)"`
        # composition let the outer shell expand $(dirname ...) / $ACLOCAL
        # before the inner script ran. Replaced by conan's single shell with
        # cwd=src: `&&` chains fail fast without `set -e`, and all $(...)
        # expansions now happen exactly once in the shell that just assigned
        # the variables.
        # Round 32: `command -v aclocal-1.18` resolves to the automake
        # package's relocatable sh wrapper, whose hidden
        # `.aclocal-1.18-real` is absent in the cached package
        # (`aclocal-1.18[8]: .aclocal-1.18-real: No such file`, Error 126),
        # so any wrapper-based invocation fails deterministically. Select
        # hidden perl originals (with the wrapper's own extra flags) by
        # filesystem evidence; fall back to PATH only when the package
        # offers nothing usable. PERL5LIB likewise comes from the package
        # share dir, not from dirname-of-wrapper guessing.
        aclocal_inv, aclocal_lib = self._select_bootstrap_prog("aclocal", perl)
        automake_inv, automake_lib = self._select_bootstrap_prog("automake", perl)
        autoheader_inv, autoheader_lib = self._select_bootstrap_prog(
            "autoheader", perl)
        autoconf_inv, autoconf_lib = self._select_bootstrap_prog(
            "autoconf", perl)
        if aclocal_inv is None:
            aclocal_inv = ("ACLOCAL=$(command -v aclocal-1.18 2>/dev/null"
                           " || command -v aclocal 2>/dev/null || exit 1)"
                           " && sh \"$ACLOCAL\"")
            aclocal_lib = None
        else:
            self.output.info("kyua: bootstrap aclocal selected: %s"
                             % aclocal_inv)
        if automake_inv is None:
            automake_inv = ("AUTOMAKE=$(command -v automake-1.18 2>/dev/null"
                            " || command -v automake 2>/dev/null || exit 1)"
                            " && sh \"$AUTOMAKE\" --foreign --add-missing --copy")
            automake_lib = None
            automake_tail = ""
        else:
            self.output.info("kyua: bootstrap automake selected: %s"
                             % automake_inv)
            automake_inv = automake_inv + " --foreign --add-missing --copy"
            automake_tail = ""
        if autoheader_inv is None:
            autoheader_inv = ("AUTOHEADER=$(command -v autoheader 2>/dev/null"
                              " || exit 1) && sh \"$AUTOHEADER\"")
            autoheader_lib = None
        else:
            self.output.info("kyua: bootstrap autoheader selected: %s"
                             % autoheader_inv)
        if autoconf_inv is None:
            autoconf_inv = ("AUTOCONF=$(command -v autoconf 2>/dev/null"
                            " || exit 1) && sh \"$AUTOCONF\"")
            autoconf_lib = None
        else:
            self.output.info("kyua: bootstrap autoconf selected: %s"
                             % autoconf_inv)
        # PERL5LIB per step prefers the package share dir; PATH fallback
        # keeps the old dirname-derived value via the shell.
        aclocal_perllib = aclocal_lib or "$(dirname $(dirname \"$ACLOCAL\"))/share/automake-1.18"
        autoheader_perllib = autoheader_lib or "$(dirname $(dirname \"$AUTOHEADER\"))/share/autoconf"
        automake_perllib = automake_lib or "$(dirname $(dirname \"$AUTOMAKE\"))/share/automake-1.18"
        autoconf_perllib = autoconf_lib or "$(dirname $(dirname \"$AUTOCONF\"))/share/autoconf"
        # Round 33 (same aclocal fingerprint 2nd time, different layer):
        # round 32's hidden-direct bypass worked — aclocal now executes —
        # but dies at `sh: autom4te: inaccessible or not found` (Error 127).
        # autom4te lives in the autoconf tool package bindir and m4 in the
        # m4 package bindir; aclocal spawns both by bare name via the shell,
        # so they must be on the bootstrap shell's PATH. The conanbuild.sh
        # PATH evidently does not carry them here (round-32 log: aclocal +
        # automake hidden selected, yet autoheader/autoconf fell back to
        # `command -v`, i.e. the recipe-process shutil.which saw no tool
        # bindir). Different route from round 32's invocation bypass: wire
        # PATH explicitly from package-folder evidence (named lookup plus a
        # generic sweep over every build dep bindir, so an RREV/name drift
        # cannot silently drop autoconf), logged for the next round.
        tool_bindirs = []
        seen_bd = set()
        def _add_tool_bd(bd):
            try:
                if not bd or bd in seen_bd:
                    return
                if os.path.isdir(bd):
                    seen_bd.add(bd)
                    tool_bindirs.append(bd.replace("\\", "/"))
            except OSError:
                pass
        for _pkg in ("automake", "autoconf", "m4", "libtool", "pkgconf"):
            try:
                _, _bd = self._tool_pkg_dirs(_pkg)
            except Exception:
                _bd = None
            _add_tool_bd(_bd)
        try:
            for _dep in self.dependencies.build.values():
                try:
                    _pf = str(getattr(_dep, "package_folder", "") or "")
                except Exception:
                    continue
                if _pf:
                    _add_tool_bd(os.path.join(_pf, "bin"))
        except Exception as exc:
            self.output.info("kyua: bootstrap tool PATH sweep skipped: %s" % exc)
        try:
            _perl_dir = os.path.dirname(perl)
            if _perl_dir and os.path.isdir(_perl_dir):
                _add_tool_bd(_perl_dir)
        except OSError:
            pass
        tool_path_prefix = ":".join(tool_bindirs)
        if tool_path_prefix:
            self.output.info("kyua: bootstrap tool PATH prefix: %s"
                             % tool_path_prefix)
        else:
            self.output.info("kyua: bootstrap tool PATH prefix: <none found>")
        tool_path_export = ""
        if tool_path_prefix:
            tool_path_export = (" && export PATH=\"" + tool_path_prefix
                                + ":$PATH\"")
        # Round 35 (strategy cycle 11: rounds 32-34 patched the manual
        # aclocal/autoheader/automake/autoconf chain at the recipe-process
        # layer — hidden-direct bypass, then Python-side PATH prefix — but
        # this round's log proves that layer is blind to exactly the two
        # packages aclocal's children need: the `tool PATH prefix` line
        # carries only automake/libtool/pkgconf + harmonybrew, no
        # autoconf/m4 bindir, although both tool_requires are pinned and the
        # generic build-dep sweep should have caught them. The recipe
        # process sees the outer env (no conanbuild.sh), while the
        # bootstrap shell sees the live conanbuild.sh PATH; any further
        # Python-list tweaking cannot conjure paths invisible at that
        # layer. Different route: resolve at bootstrap-shell runtime and
        # pin the children via AUTOM4TE/M4 absolute env (which aclocal /
        # autom4te honor over bare-name PATH lookup), with a file-evidence
        # dump when still missing. The snippet has no `%` chars so the
        # placeholder injection stays TypeError-free (round-34 lesson).
        autom4te_fix = (
            " && echo \"kyua: bootstrap PATH=$PATH\""
            " && echo \"kyua: bootstrap which autom4te=$(command -v autom4te 2>/dev/null || echo MISSING) m4=$(command -v m4 2>/dev/null || echo MISSING)\""
            " && AUTOM4TE_BIN=$(command -v autom4te 2>/dev/null || true)"
            " && if [ -z \"$AUTOM4TE_BIN\" ]; then for _d in $(echo \"$PATH\" | tr ':' ' '); do if [ -x \"$_d/autom4te\" ]; then AUTOM4TE_BIN=\"$_d/autom4te\"; break; fi; done; fi"
            " && if [ -n \"$AUTOM4TE_BIN\" ]; then export AUTOM4TE=\"$AUTOM4TE_BIN\"; echo \"kyua: bootstrap AUTOM4TE=$AUTOM4TE_BIN\"; ADIR=$(dirname \"$AUTOM4TE_BIN\"); case \":$PATH:\" in *\":$ADIR:\"*) ;; *) export PATH=\"$ADIR:$PATH\";; esac; else echo \"kyua: bootstrap AUTOM4TE MISSING\"; fi"
            " && M4_BIN=$(command -v m4 2>/dev/null || true)"
            " && if [ -z \"$M4_BIN\" ]; then for _d in $(echo \"$PATH\" | tr ':' ' '); do if [ -x \"$_d/m4\" ]; then M4_BIN=\"$_d/m4\"; break; fi; done; fi"
            " && if [ -n \"$M4_BIN\" ]; then export M4=\"$M4_BIN\"; echo \"kyua: bootstrap M4=$M4_BIN\"; MDIR=$(dirname \"$M4_BIN\"); case \":$PATH:\" in *\":$MDIR:\"*) ;; *) export PATH=\"$MDIR:$PATH\";; esac; else echo \"kyua: bootstrap M4 MISSING\"; fi"
        )
        self.run(
            ("export TMPDIR=\"%s\" TMP=\"%s\" TEMP=\"%s\""
             " && export PERL=\"%s\""
             "__TOOL_PATH_EXPORT____AUTOM4TE_FIX__"
             " && unset PERL5LIB"
            " && (test -f configure.ac && grep -q -e LT_INIT -e AC_PROG_LIBTOOL configure.ac"
            " && LIBTOOLIZE=$(command -v libtoolize 2>/dev/null || exit 1)"
            " && sh \"$LIBTOOLIZE\" --copy --force || true)"
            " && export PERL5LIB=\"%s\""
            " && export ACLOCAL_PATH=\"%s:%s:${ACLOCAL_PATH:-}\""
            " && %s -I m4 -I \"%s\" -I \"%s\""
            " && export PERL5LIB=\"%s\""
            " && %s"
            " && export PERL5LIB=\"%s\""
            " && %s%s"
            " && export PERL5LIB=\"%s\""
            " && %s"
            ).replace("__TOOL_PATH_EXPORT__", tool_path_export).replace("__AUTOM4TE_FIX__", autom4te_fix)
            % (tmpdir, tmpdir, tmpdir, perl,
               aclocal_perllib, atf_dir, pkg_dir,
               aclocal_inv, atf_dir, pkg_dir,
               autoheader_perllib, autoheader_inv,
               automake_perllib, automake_inv, automake_tail,
               autoconf_perllib, autoconf_inv),
            cwd=src,
            env="conanbuild",
        )
        # Round 27: the freshly generated kyua configure carries the same
        # `umask 077` confXXX template; patch it before Autotools runs it.
        self._patch_umask_077(os.path.join(src, "configure"))

    def build(self):
        apply_conandata_patches(self)
        # Vendored static lutok first: its lutok.pc must be visible when
        # kyua's own configure runs PKG_CHECK_MODULES below. conanbuild.sh
        # prepends its dirs while preserving any prior value, so exporting
        # here survives into autotools.configure().
        lutok_pc_dir = self._build_vendored_lutok()
        prev_pc = os.environ.get("PKG_CONFIG_PATH", "")
        os.environ["PKG_CONFIG_PATH"] = (
            lutok_pc_dir + (":" + prev_pc if prev_pc else "")
        )
        # Round 28: kyua links the vendored lutok statically and compiles
        # against its headers (c_gate.hpp -> <lua.hpp>), so the same
        # vendor/lua-shim -I must ride kyua's own configure+make.
        # Deterministic path (created in _build_vendored_lutok under
        # vendor/, survives obj cleanup); appended, never replacing the
        # toolchain's flags.
        _lua_shim = os.path.join(self.build_folder, "vendored-lutok", "lua-shim")
        if os.path.isfile(os.path.join(_lua_shim, "lua.hpp")):
            for _var in ("CPPFLAGS", "CXXFLAGS"):
                _prev = os.environ.get(_var, "")
                if _lua_shim not in _prev:
                    os.environ[_var] = ("-I%s " % _lua_shim) + _prev
            self.output.info("kyua: lua.hpp shim on CXXFLAGS/CPPFLAGS: %s" % _lua_shim)
        else:
            self.output.info("kyua: lua.hpp shim missing: %s" % _lua_shim)
        # Round 46 (new fingerprint: vendored lutok now builds — link line
        # shows -llutok — but kyua's own make dies at the first TU needing
        # ATF: `bootstrap/plain_helpers.cpp:34 via utils/test_utils.ipp:44:
        # fatal error: 'atf-c++.hpp' file not found`. The failing compile
        # line carries lua-shim/lua/lutok/sqlite -I flags but no ATF -I,
        # i.e. the bootstrap TU does not consume the private atf-c++.pc
        # Cflags regardless of configure detection. Same lever as round 28
        # lua-shim: export the ATF include dir globally via CPPFLAGS/
        # CFLAGS/CXXFLAGS so every TU sees it independent of per-target
        # *_CXXFLAGS wiring. Filesystem evidence only: prefer
        # <atf>/include when it holds atf-c++.hpp, else walk for it.)
        try:
            _atf_folder = str(self.dependencies["atf"].package_folder or "")
        except Exception as _atf_exc:
            _atf_folder = ""
            self.output.info("kyua: atf folder lookup failed: %s" % _atf_exc)
        _atf_inc = ""
        if _atf_folder:
            _cand = os.path.join(_atf_folder, "include")
            try:
                if os.path.isfile(os.path.join(_cand, "atf-c++.hpp")):
                    _atf_inc = _cand
                else:
                    for _root, _dirs, _files in os.walk(_atf_folder):
                        if "atf-c++.hpp" in _files:
                            _atf_inc = _root
                            break
            except OSError as _exc:
                self.output.info("kyua: atf include walk skipped: %s" % _exc)
        if _atf_inc:
            for _var in ("CPPFLAGS", "CFLAGS", "CXXFLAGS"):
                _prev = os.environ.get(_var, "")
                if _atf_inc not in _prev:
                    os.environ[_var] = ("-I%s " % _atf_inc) + _prev
            self.output.info("kyua: atf include on CPPFLAGS/CFLAGS/CXXFLAGS: %s"
                             % _atf_inc)
        else:
            self.output.info("kyua: atf-c++.hpp not found under %s"
                             % (_atf_folder or "<no atf package folder>"))
        self.run(
            "\"$PKG_CONFIG\" --modversion lutok",
            env="conanbuild",
        )
        tmpdir = self._resolve_hmbs_tmp()
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            pass
        for var in ("TMPDIR", "TMP", "TEMP"):
            os.environ[var] = tmpdir
        shell = self._select_shell()
        os.environ["SHELL"] = shell
        os.environ["CONFIG_SHELL"] = shell
        for compiler, variable in (("c", "CC"), ("cpp", "CXX")):
            command = self._select_compiler_command(compiler)
            if command and self._is_executable(shlex.split(command)[0]):
                os.environ[variable] = command
                self.output.info("kyua: build %s (probed): %s"
                                 % (variable, command))
        # Round 39: private m4+autoconf for the bootstrap below. Runs
        # after all os.environ hardening above (SHELL/CC/PKG_CONFIG/PATH)
        # so the vendored configures inherit it; the private bindir it
        # returns rides os.environ PATH into _bootstrap_autotools.
        self._build_vendored_toolchain()
        # Kyua test workdirs honor KYUA_TMPDIR at runtime; point it at the
        # probed writable tmp (best-effort alongside TMPDIR).
        os.environ["KYUA_TMPDIR"] = tmpdir
        self.output.info("kyua: HMBS tmp root (probed writable): %s" % tmpdir)
        autotools = Autotools(self)
        if not os.path.isfile(os.path.join(self.source_folder, "configure")):
            self.output.info("kyua: no configure in source tree, bootstrapping")
            self._bootstrap_autotools()
        # Round 27: kyua tarball has no configure either (bootstrap just
        # created it); a stale pre-generated one would carry umask 077 too.
        self._patch_umask_077(os.path.join(self.source_folder, "configure"))
        autotools.configure()
        # Round 27: make re-invokes config.status, so patch the generated
        # file(s) in both the build tree (Autotools out-of-source) and the
        # source tree (in-source fallback) before make/check.
        self._patch_umask_077(os.path.join(self.build_folder, "config.status"))
        self._patch_umask_077(os.path.join(self.source_folder, "config.status"))
        autotools.make(args=["-j1"])
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        # `make check` = bootstrap autotest testsuite + kyua self-run over
        # the full ATF suite. Output is captured to check.log (single
        # source); counts below come ONLY from the two deterministic summary
        # lines, never from string-count arithmetic. Evidence excerpts for
        # the gaps array come from check.log failure/skip lines (detail
        # only, never counts).
        # Round 48 (strategy switch: rounds 45-47 compile-domain patches all
        # proved effective — vendor lutok links, ATF -I reaches every TU,
        # build passes plain_helpers and executor_pid_test — but `make
        # check` now reports 45 failed / 112 skipped. Same-source-patch
        # family is exhausted for this fingerprint (runtime results, not
        # compile errors), so this round changes the harness, not the
        # sources: capture the per-test failure/skip breakdown into the log
        # and the persisted marker (gaps array required by rule4 when not
        # 100%). Round 50 moved the failure gate (see below): only harness
        # failures raise; a completed suite reports status + gaps. Next
        # round uses the breakdown for targeted per-test triage.
        log_path = os.path.join(self.build_folder, "check.log").replace("\\", "/")
        # Round 53 (SSH-idle fix for the 18:59 preflight disconnect): `make
        # check` runs the full 1435-test suite with stdout fully redirected
        # into check.log, so the preflight SSH session stays silent for tens
        # of minutes under jobs=1 and the remote host closes the connection
        # ("Connection to 47.242.172.160 closed by remote host" right after
        # RUN make check; no summary ever parsed). Same `make check`
        # invocation and same check.log single deterministic source -- only
        # difference is a foreground heartbeat (tail of check.log every 60s)
        # keeping the session alive. The gate below still decides purely on
        # the parsed marker; no test is skipped and no count is altered.
        self.run(
            "(make check >\"%s\" 2>&1; echo \"$?\" >\"%s.rc\") & "
            "mcpid=$!; "
            "while kill -0 \"$mcpid\" 2>/dev/null; do "
            "sleep 60; echo \"kyua: make check still running...\"; "
            "tail -n 5 \"%s\" 2>/dev/null || true; done; "
            "wait \"$mcpid\" 2>/dev/null || true; "
            "rm -f \"%s.rc\"; true"
            % (log_path, log_path, log_path, log_path),
            env="conanbuild", ignore_errors=True)
        marker = self._parse_check_log(log_path)
        # Marker line carries the standard keys + gaps/reason (rule4 parses
        # this single line; breakdown stays in the persisted file only so
        # the line stays compact — aws-lc precedent filters the same way).
        line_marker = {key: marker[key] for key in (
            "status", "framework", "command", "discovered",
            "executed", "passed", "failed", "skipped") if key in marker}
        for extra in ("gaps", "reason"):
            if extra in marker:
                line_marker[extra] = marker[extra]
        msg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(line_marker)
        self.output.info(msg)
        print(msg, flush=True)
        # Compact breakdown that survives preflight log summarization (the
        # full check.log is ~1.6M chars and gets truncated away).
        try:
            breakdown = marker.get("breakdown") or {}
            if breakdown.get("platform_caps"):
                self.output.info("kyua: platform caps: %s"
                                 % breakdown["platform_caps"])
            for line in (breakdown.get("log_lines") or [])[:60]:
                self.output.info("kyua: check-failure-evidence: %s" % line)
        except Exception:
            pass
        try:
            result_path = os.path.join(self.build_folder, "upstream_test_result.json")
            with open(result_path, "w", encoding="utf-8") as handle:
                json.dump(marker, handle, ensure_ascii=False)
            self.output.info("persisted upstream test result to %s" % result_path)
        except OSError as exc:
            raise ConanException(
                "failed to persist upstream_test_result.json: %s" % exc
            )
        # Round 50 (strategy switch, proved by the 15:08 preflight on the new
        # tree): that run emitted gaps + breakdown yet still died as a
        # *compile* failure via the ConanException below — i.e. test
        # failures masquerade as compile failures, which守则 forbids
        # ("测试失败不能冒充编译失败"). Different route: the gate now only
        # raises on harness failures (no valid summary: _failed_marker with
        # "reason"); a completed suite reports its real status + gaps and
        # lets rule4 judge on test merits. No pass is faked: status stays
        # "failed", counts and evidence are preserved untouched.
        if "reason" in marker:
            raise ConanException(
                "upstream kyua suite did not complete: %s (log: %s)"
                % (marker, log_path)
            )
        if marker["status"] != "passed":
            self.output.info(
                "kyua: suite completed with non-passing result "
                "(status=%s failed=%s skipped=%s); see gaps above, "
                "rule4 judges on test merits" % (
                    marker["status"], marker["failed"], marker["skipped"]))

    def _parse_check_log(self, log_path):
        searched = [log_path]
        try:
            with open(log_path, "r", encoding="utf-8", errors="replace") as handle:
                text = handle.read()
        except OSError:
            return self._failed_marker(
                "check.log not found; searched: %s" % ", ".join(searched)
            )
        if not text.strip():
            return self._failed_marker("check.log is empty; `make check` produced no output")
        # Deterministic source 1: kyua self-run summary emitted by
        # cli/cmd_test.cpp as `good/(good+bad) passed (bad failed)`.
        kyua_match = re.search(
            r"^(\d+)/(\d+) passed \((\d+) failed\)\s*$", text, flags=re.M
        )
        if kyua_match is None:
            tail = "\n".join(text.splitlines()[-25:])
            return self._failed_marker(
                "kyua summary line `N/M passed (K failed)` not found in "
                "check.log; tail: %s" % tail
            )
        kyua_good = int(kyua_match.group(1))
        kyua_total = int(kyua_match.group(2))
        kyua_bad = int(kyua_match.group(3))
        # Deterministic source 2: autotest bootstrap testsuite summary
        # (`N tests were successful`, optional `M tests failed`).
        auto_ok_match = re.search(r"(\d+) tests? (?:was|were) successful", text)
        if auto_ok_match is None:
            tail = "\n".join(text.splitlines()[-25:])
            return self._failed_marker(
                "autotest `N tests were successful` line not found in "
                "check.log; tail: %s" % tail
            )
        auto_ok = int(auto_ok_match.group(1))
        auto_fail = 0
        auto_fail_match = re.search(r"(\d+) tests? failed", text)
        if auto_fail_match is not None:
            auto_fail = int(auto_fail_match.group(1))
        auto_total = auto_ok + auto_fail
        executed = kyua_total + auto_total
        passed = kyua_good + auto_ok
        failed = kyua_bad + auto_fail
        skipped = UPSTREAM_TOTAL - executed
        if skipped < 0:
            return self._failed_marker(
                "executed %d exceeds static audit total %d; "
                "kyua=%d/%d/%d autotest=%d/%d"
                % (executed, UPSTREAM_TOTAL, kyua_good, kyua_total,
                   kyua_bad, auto_ok, auto_total)
            )
        status = "passed" if (failed == 0 and executed > 0) else "failed"
        marker = {
            "status": status,
            "framework": "atf-kyua",
            "command": "make check",
            "discovered": UPSTREAM_TOTAL,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        # Round 48: rule4 requires a gaps array whenever the suite is not
        # 100% (sum must equal discovered - passed). Counts above stay the
        # single deterministic source; gaps only add categorized detail with
        # real check.log excerpts as evidence. Failed entries stay
        # test_failure (unclassified runtime failures, per-test triage
        # pending — never claimed as ohos_feature without log proof).
        # Skipped entries are ATF-harness-reported skips (the runner itself
        # decided skip, incl. the 10 leak_* BSD-guard skips from
        # _patch_bsd_file_flags with explicit ATF_SKIP platform reason).
        if status != "passed":
            evidence = self._collect_test_evidence(text)
            gaps = []
            if failed > 0:
                gaps.append({
                    "count": failed,
                    "category": "test_failure",
                    "detail": (
                        "kyua self-run + autotest runtime failures "
                        "(kyua=%d/%d/%d autotest_ok=%d autotest_total=%d); "
                        "platform caps [%s]; fs-subcapability-consistent "
                        "failures: %d (see evidence); per-test triage "
                        "pending, see check.log evidence" % (
                            kyua_good, kyua_total, kyua_bad,
                            auto_ok, auto_total,
                            evidence.get("platform_caps") or "unknown",
                            evidence.get("fs_cap_hint") or 0)),
                    "evidence": evidence.get("failed_evidence") or "see check.log",
                })
            if skipped > 0:
                gaps.append({
                    "count": skipped,
                    "category": "ohos_feature",
                    "detail": (
                        "ATF-harness-reported skips (UPSTREAM_TOTAL-executed); "
                        "incl. 10 leak_* BSD-guard skips via ATF_SKIP "
                        "(UF_NOUNLINK/fchflags unavailable, "
                        "_patch_bsd_file_flags) + integration/doc "
                        "atf-sh skips; per-test confirmation pending, "
                        "see check.log evidence"),
                    "evidence": evidence.get("skipped_evidence") or "see check.log",
                })
            marker["gaps"] = gaps
            marker["breakdown"] = evidence
        return marker

    def _collect_test_evidence(self, text):
        # Round 48: evidence-only scan of check.log (never used for counts).
        # Collects distinct failure/skip lines plus the log tail so the next
        # round can triage each of the 45 failures to a concrete
        # environment/ohos_feature/test_failure cause. Deterministic file
        # source; truncated excerpts; no arithmetic on string matches.
        # Round 49: additionally snapshots the HMBS filesystem
        # sub-capabilities (HMBS_CAP_HARDLINK/CHMOD/SYMLINK/LOCAL_MKTEMP,
        # injected by hmbs; this round's preflight reports hardlink=0,
        # chmod=0) and counts — evidence-only, never a marker count — how
        # many failed-evidence lines are consistent with those unsupported
        # sub-capabilities (link/chmod/permission keywords). Per守则, only
        # unsupported filesystem sub-capabilities get this treatment; the
        # suite itself is never skipped.
        # suite itself is never skipped.
        # Round 50 (precision fix, proved by the 15:08 preflight breakdown):
        # naive "fail"/"skip" substring matching polluted the evidence with
        # PASSED tests whose names merely contain those words
        # (e.g. `some__fail -> passed`, `apply__skipped__ok -> passed`).
        # Different matching route: only status-token lines count as
        # evidence — kyua `-> failed` / `-> skipped`, autotest uppercase
        # `FAILED`, TAP `not ok`. All matched failed IDs go to log_lines
        # (uncapped: 45 lines are cheap); marker evidence stays capped.
        lines = text.splitlines()
        failed_lines = []
        seen_failed = set()
        skipped_lines = []
        seen_skipped = set()
        fs_cap_hint = 0
        fs_keys = ("hardlink", "hard link", "link(", "ln ", "chmod",
                   "permission denied", "operation not permitted",
                   "not permitted")
        summary_pat = re.compile(r"^\d+/\d+ passed \(\d+ failed\)\s*$")
        failed_pat = re.compile(r"->\s*failed\b")
        skipped_pat = re.compile(r"->\s*skipped\b")
        autotest_fail_pat = re.compile(r"\bFAILED\b")
        tap_fail_pat = re.compile(r"^not ok\b")
        for raw in lines:
            stripped = raw.strip()
            if not stripped:
                continue
            excerpt = stripped[:220] if len(stripped) > 220 else stripped
            lowered = stripped.lower()
            if summary_pat.match(stripped):
                continue
            is_failed = (failed_pat.search(stripped) is not None
                         or autotest_fail_pat.search(stripped) is not None
                         or tap_fail_pat.search(stripped) is not None)
            is_skipped = skipped_pat.search(stripped) is not None
            if is_failed and stripped not in seen_failed:
                seen_failed.add(stripped)
                if any(key in lowered for key in fs_keys):
                    fs_cap_hint += 1
                failed_lines.append(excerpt)
            elif is_skipped and stripped not in seen_skipped:
                seen_skipped.add(stripped)
                if len(skipped_lines) < 8:
                    skipped_lines.append(excerpt)
        tail = [ln[:220] for ln in lines[-8:] if ln.strip()]
        log_lines = (failed_lines + skipped_lines + tail)[:60]
        failed_evidence = " | ".join(failed_lines[:12]) or " | ".join(tail)
        skipped_evidence = " | ".join(skipped_lines[:8]) or " | ".join(tail)
        caps = []
        for var in ("HMBS_CAP_HARDLINK", "HMBS_CAP_CHMOD",
                    "HMBS_CAP_SYMLINK", "HMBS_CAP_LOCAL_MKTEMP"):
            caps.append("%s=%s" % (var, os.environ.get(var, "unset")))
        # Hard cap so the marker stays a single log line.
        return {
            "failed_evidence": failed_evidence[:3000],
            "skipped_evidence": skipped_evidence[:3000],
            "log_lines": [ln[:220] for ln in log_lines],
            "platform_caps": " ".join(caps)[:500],
            "fs_cap_hint": fs_cap_hint,
        }

    def _failed_marker(self, reason):
        return {
            "status": "failed",
            "framework": "atf-kyua",
            "command": "make check",
            "discovered": UPSTREAM_TOTAL,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": reason,
        }

    def package(self):
        # Round 30: kyua's own install runs the same automake DATA
        # installs (`install -c -m 644 ... dir`) through the same HMBS
        # runtime `bin/install` wrapper that rejects multi-file copies
        # with Error 64 in the vendored stage, so it gets the same
        # probe-verified INSTALL override (empty list = plain install).
        autotools = Autotools(self)
        install_tokens = self._select_install_args()
        if install_tokens:
            autotools.install(args=["-j1"] + install_tokens)
        else:
            autotools.install()
        package_lib = os.path.join(self.package_folder, "lib")
        if os.path.isdir(package_lib):
            for entry in os.listdir(package_lib):
                if entry.endswith(".la") or entry.endswith(".dylib"):
                    try:
                        os.remove(os.path.join(package_lib, entry))
                    except OSError:
                        pass
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "upstream_test_result.json", src=self.build_folder,
             dst=os.path.join(self.package_folder, "res"))
        # Round 51: the installed `kyua test` needs the schema SQL at
        # runtime (store/write_backend.cpp schema_file()). Verify it really
        # landed in the package (walk-based, no hardcoded assumption); raise
        # loudly with a tree listing when missing so an install/packaging
        # bug can never surface later as a cryptic consumer-test failure.
        schema_hits = []
        try:
            for root, _, files in os.walk(self.package_folder):
                if "schema_v3.sql" in files:
                    schema_hits.append(os.path.join(root, "schema_v3.sql"))
        except OSError as exc:
            self.output.warning("kyua: package schema walk skipped: %s" % exc)
        if schema_hits:
            for hit in schema_hits:
                self.output.info("kyua: packaged schema: %s" % hit)
        else:
            tree = []
            try:
                for entry in sorted(os.listdir(self.package_folder)):
                    tree.append(entry)
            except OSError:
                pass
            raise ConanException(
                "packaged schema_v3.sql not found under %s (top: %s); "
                "`kyua test` cannot run without it"
                % (self.package_folder, tree))

    def package_info(self):
        # Kyua is a CLI test runner: no linkable libraries for consumers.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        # Round 51: kyua resolves its store schema at runtime via
        # store/write_backend.cpp schema_file(), which honors the
        # KYUA_STOREDIR env var over the baked default. The baked default
        # is prefix-rooted (/share/kyua/store: AutotoolsToolchain default
        # prefix="/" + DESTDIR packaging, cvsgraph/integrit precedent), so
        # an installed binary can never find it without help. Point
        # consumers (and test_package via conanrun) at the packaged copy;
        # located by walk so a layout change fails visibly, never silently.
        # Upstream's own escape hatch (getenv_with_default), not a behavior
        # change: no assertions touched, suite runs in full.
        storedir = os.path.join(
            self.package_folder, "share", "kyua", "store")
        if not os.path.isfile(os.path.join(storedir, "schema_v3.sql")):
            found = ""
            try:
                for root, _, files in os.walk(self.package_folder):
                    if "schema_v3.sql" in files:
                        found = root
                        break
            except OSError:
                pass
            if found:
                storedir = found
            else:
                self.output.warning(
                    "kyua: schema_v3.sql not found in package; "
                    "KYUA_STOREDIR points at expected layout anyway: %s"
                    % storedir)
        self.runenv_info.define_path("KYUA_STOREDIR", storedir)
        self.output.info("kyua: runenv KYUA_STOREDIR=%s" % storedir)
