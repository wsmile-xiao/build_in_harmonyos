#!/usr/bin/env python3
"""Conan recipe — cronolog 1.6.2-rpk (log rotation utility).

Build system: autotools (release tarball ships a pre-generated ./configure).
Source: https://github.com/fordmason/cronolog (tarball cronolog-1.6.2.tar.gz)

The "-rpk" suffix is the Debian/Ubuntu packaging revision for the upstream
1.6.2 release (see https://repology.org/project/cronolog/versions);
the source tarball is the upstream 1.6.2 archive.

Adaptation notes:
  * No registry dependencies — pure C, only libc at runtime.
    cronosplit is a perl helper script, shipped as-is (not exercised).
  * The 1.6.2 configure predates config.guess triplets entirely
    (no --build/--host support, no config.guess in the tarball), so it
    simply honours $CC from the Conan toolchain — no triplet patch needed.
  * Upstream ships no test suite (testsuite/ README: "not yet written"),
    so build() runs no `make check`; functional verification is done by
    test_package driving the real binary (R34).

Rules compliance:
  R32: settings.os validated with in ("Linux", "OHOS").
  R33: Compiler / flags come from the Conan toolchain, never bare shell vars.
  R38: Executable tool — commands.json declared at the software level.
"""
import os
import re
import shutil
from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


# install wrapper (E098/E174 family): the HMBS install shim accepts only
# single-file two-arg invocations (`[ $# -eq 2 ] || exit 64`, EX_USAGE),
# while automake's install-man batches ALL man_MANS files into one
# `$(INSTALL_DATA) $$files $(mandir)` call -> Error 64. This wrapper
# copies SRC... DEST (DEST may be a directory), same precedent as the
# install shims in chicken 5.4.0 / slang 2.3.3 / lzop 1.04.
_INSTALL_WRAPPER = r"""#!/bin/sh
# install wrapper — multi-file install replacement for HarmonyOS (E098/E174)
set -e
while [ $# -gt 0 ]; do
  case "$1" in
    -c) shift ;;
    -m) shift 2 ;;
    -d) shift ;;
    -g|-o|-t) shift 2 ;;
    -*) shift ;;
    *) break ;;
  esac
done
n=$#
if [ "$n" -lt 2 ]; then
  echo "install-wrapper: expected SRC... DEST" >&2
  exit 1
fi
eval "dest=\"\${$n}\""
i=1
while [ "$i" -lt "$n" ]; do
  eval "s=\"\${$i}\""
  if [ -d "$dest" ]; then
    cp -f "$s" "$dest/" || exit 1
  else
    cp -f "$s" "$dest" || exit 1
  fi
  i=$((i+1))
done
"""


class CronologConan(ConanFile):
    name = "cronolog"
    version = "1.6.2-rpk"
    description = "Log rotation software that splits log streams into date-templated files"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/fordmason/cronolog"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # CLI tool, not a library (R38: commands.json declared at software level)
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # No dependencies — pure C, links only against libc.
        pass

    def layout(self):
        basic_layout(self)

    def validate(self):
        # R32: settings.os must be checked with in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"cronolog 1.6.2-rpk only supports Linux and OHOS, got {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # HarmonyOS /tmp is read-only (erofs, readonly_tmp). HMBS injects a
        # task-private writable TMPDIR/TMP/TEMP; propagate it into the Conan
        # buildenv so clang temp objects and configure children honour it.
        # Fall back to a build-folder-local tmp dir when the injection is
        # absent (e.g. local runs). Do NOT shadow mktemp with an always-fail
        # shim: this vintage 1.6.2 configure contains no mktemp/umask logic
        # (verified 0 matches), and a global failing mktemp breaks legitimate
        # temp-file creation during the compiler probe, surfacing as
        # "C compiler cannot create executables". E011 (umask 077) is already
        # mitigated by os.umask(0) in build().
        tmpdir = (
            os.environ.get("TMPDIR")
            or os.environ.get("TMP")
            or os.environ.get("TEMP")
        )
        if not tmpdir or not os.path.isdir(tmpdir):
            tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMP"] = tmpdir
        os.environ["TEMP"] = tmpdir
        env = Environment()
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)
        env.define("TEMP", tmpdir)
        # Profile ohos-aarch64 buildenv injects CONFIG_SHELL/SHELL pointing
        # to the OHOS HNP bash, which is inaccessible in some HMBS preflight
        # containers (configure[2348] `${CONFIG_SHELL-/bin/sh} config.status`
        # dies with "inaccessible or not found") and has getcwd defects on
        # HMDFS (classads/DRAFT-6487, guile precedent). HMBS injects a working
        # SHELL=/bin/sh; pin both to /bin/sh so configure/config.status/make
        # all use the capability-tested shell. Inline CONFIG_SHELL/SHELL
        # prefix in build() run commands shadows any stale profile value.
        env.define("SHELL", "/bin/sh")
        env.define("CONFIG_SHELL", "/bin/sh")
        env.vars(self).save_script("hmos_env")

        tc = AutotoolsToolchain(self)
        # Vintage 1999 configure probes the compiler with K&R
        # `main(){return(0);}` (implicit int, no prototype). Modern clang
        # promotes implicit-int / implicit-function-declaration to hard
        # errors, which this configure reports only as the opaque
        # "C compiler cannot create executables". Downgrade those two
        # diagnostics to warnings; this changes no language semantics,
        # it only lets the trivial conftest probe link as intended.
        tc.extra_cflags.extend([
            "-Wno-error=implicit-int",
            "-Wno-error=implicit-function-declaration",
        ])
        tc.generate()

    def _probe_executable(self, path):
        # Target-side exec probe: True iff `path --version` actually runs in
        # the same context configure will use (file existence alone is not
        # enough; a stale toolchain path fails exec with mksh's
        # "inaccessible or not found").
        if not path or not os.path.isfile(path):
            return False
        try:
            self.run(f'"{path}" --version')
            return True
        except Exception:
            return False

    def _resolve_compiler(self, kind, fallback_names):
        # R33: the Conan toolchain stays the primary compiler source. Only
        # when the configured absolute path cannot be executed on the target
        # (proven by _probe_executable, not by guessing) do we fall back to
        # a PATH-resolved compiler for this native build, and we log the
        # decision so the preflight log shows exactly what was picked.
        # NOTE: tools.build:compiler_executables is a dict conf
        # (systemd 261 / zsv 1.4.3 precedent); the per-key `:c` form is not
        # a registered conf and raises ConanException when absent, so fetch
        # the dict with a default instead.
        try:
            ce = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
        except Exception:
            ce = {}
        configured = ce.get(kind)
        self.output.info(f"[cronolog] toolchain {kind} compiler: {configured!r}")
        if configured and self._probe_executable(configured):
            self.output.info(f"[cronolog] using toolchain {kind} compiler: {configured}")
            return configured
        if configured:
            self.output.warning(
                f"[cronolog] toolchain {kind} compiler '{configured}' is not "
                f"executable on target; searching PATH"
            )
        for name in fallback_names:
            found = shutil.which(name)
            self.output.info(f"[cronolog] which({name}) -> {found!r}")
            if found and self._probe_executable(found):
                self.output.warning(
                    f"[cronolog] using PATH-resolved {kind} compiler '{found}' "
                    f"(toolchain path unusable)"
                )
                return found
        self.output.warning(f"[cronolog] no executable {kind} compiler found; leaving configure to decide")
        return None

    def build(self):
        previous_umask = os.umask(0)
        try:
            apply_conandata_patches(self)
            # HMDFS: getcwd() fails inside some Conan build dirs (broken parent
            # path chain), which makes autoconf's `ac_pwd=\`pwd\`` sanity check
            # die with "configure: error: working directory cannot be determined".
            # Seed $PWD and chdir to the build folder so the shell pwd builtin
            # resolves the cwd logically (sipcalc/libclastfm/lzop precedent).
            bf = self.build_folder
            if os.path.isdir(bf):
                os.chdir(bf)
                os.environ["PWD"] = bf
            # The toolchain-configured absolute compiler path may not be
            # executable in this sandbox (config.log: `.../clang:
            # inaccessible or not found`). Verify on target and hand a
            # working CC/CXX to configure *via shell environment prefix*
            # (`CC=... ./configure`), NOT via configure positional args.
            # This 1.6.2 vintage configure predates autoconf VAR=VALUE
            # argument parsing: any `CC=...` token after `./configure`
            # is treated as a host/target alias, dying with
            # "invalid host type" + "can only configure for one host and
            # one target at a time" (preflight 2026-09-10 evidence).
            # A `CC=...` env prefix is stripped by the shell before
            # configure sees argv, so it works on any vintage while still
            # overriding the broken toolchain CC exported by conanbuild.sh
            # (prefix assignment shadows the sourced export for that one
            # command; CFLAGS/LDFLAGS from the toolchain still apply).
            # R33: the Conan toolchain stays the primary compiler source;
            # PATH fallback is used only when the configured path fails
            # the on-target exec probe below.
            cc = self._resolve_compiler("c", ("clang", "cc", "gcc"))
            cxx = self._resolve_compiler("cpp", ("clang++", "c++", "g++"))
            # Ensure child configure/config.status/make never see the stale
            # profile SHELL/CONFIG_SHELL even if a code path forgets the
            # inline prefix below.
            os.environ["SHELL"] = "/bin/sh"
            os.environ["CONFIG_SHELL"] = "/bin/sh"
            autotools = Autotools(self)
            if cc or cxx:
                env_prefix = ""
                if cc:
                    env_prefix += f'CC="{cc}" '
                    os.environ["CC"] = cc
                if cxx:
                    env_prefix += f'CXX="{cxx}" '
                    os.environ["CXX"] = cxx
                configure_script = os.path.join(self.source_folder, "configure")
                self.output.info(f"[cronolog] configure env override: {env_prefix.strip()}")
                try:
                    # CONFIG_SHELL/SHELL prefix shadows the profile buildenv
                    # value (/data/service/hnp/bin/bash) which is
                    # "inaccessible or not found" in HMBS preflight and has
                    # getcwd defects on HMDFS. `sh` explicit launch also
                    # avoids noexec direct-exec failures (guile precedent).
                    self.run(f'CONFIG_SHELL=/bin/sh SHELL=/bin/sh {env_prefix}sh "{configure_script}" --prefix="{self.package_folder}"')
                except Exception:
                    log_path = os.path.join(bf, "config.log")
                    if os.path.isfile(log_path):
                        self.output.info("--- config.log tail (cronolog) ---")
                        with open(log_path, encoding="utf-8", errors="replace") as f:
                            lines = f.readlines()
                        for line in lines[-100:]:
                            self.output.info(line.rstrip())
                        self.output.info("--- end config.log tail ---")
                    raise
            else:
                try:
                    self.run(f'CONFIG_SHELL=/bin/sh SHELL=/bin/sh sh "{self.source_folder}/configure" --prefix="{self.package_folder}"')
                except Exception:
                    # This vintage configure hides the real clang error behind
                    # "C compiler cannot create executables". Dump the tail of
                    # config.log so the next preflight log shows the actual
                    # compiler diagnostic instead of the opaque summary.
                    log_path = os.path.join(bf, "config.log")
                    if os.path.isfile(log_path):
                        self.output.info("--- config.log tail (cronolog) ---")
                        with open(log_path, encoding="utf-8", errors="replace") as f:
                            lines = f.readlines()
                        for line in lines[-100:]:
                            self.output.info(line.rstrip())
                        self.output.info("--- end config.log tail ---")
                    raise
            # R9: single job — parallel make hits HMDFS jobserver fifo EPERM (E074)
            autotools.make(args=["-j1"])
        finally:
            os.umask(previous_umask)

    def package(self):
        # HMBS install shim rejects anything but single-file two-arg
        # invocations (`[ $# -eq 2 ] || exit 64`, EX_USAGE): automake's
        # install-man batches cronolog.1m + cronosplit.1m into one
        # `$(INSTALL_DATA) $files $(mandir)` call, and even the single
        # binary install arrives as `install -c src dest` (3 argv including
        # `-c`), tripping the same gate. Preflight evidence 2026-09-10 (x3):
        # docs (wrapper-patched INSTALL_DATA) staged fine while sbin/ never
        # materialised. Redirect INSTALL_DATA/INSTALL_PROGRAM/INSTALL_SCRIPT
        # to a multi-file-capable wrapper in EVERY generated Makefile under
        # the build tree (lzop 1.04 precedent, extended to PROGRAM/SCRIPT).
        wrapper = os.path.join(self.build_folder, "install-wrapper.sh")
        with open(wrapper, "w", encoding="utf-8", newline="\n") as f:
            f.write(_INSTALL_WRAPPER)
        try:
            os.chmod(wrapper, 0o755)
        except OSError as exc:
            self.output.warning(f"[cronolog] chmod wrapper failed: {exc}")
        patched = 0
        for root, _dirs, files in os.walk(self.build_folder):
            for name in files:
                if name != "Makefile":
                    continue
                makefile = os.path.join(root, name)
                with open(makefile, "r", encoding="utf-8") as f:
                    content = f.read()
                new_content = content
                for var in ("INSTALL_DATA", "INSTALL_PROGRAM", "INSTALL_SCRIPT"):
                    new_content = re.sub(
                        r"^" + var + r"\s*=.*$",
                        "{} = {}".format(var, wrapper),
                        new_content,
                        flags=re.MULTILINE,
                    )
                if new_content != content:
                    with open(makefile, "w", encoding="utf-8", newline="\n") as f:
                        f.write(new_content)
                    patched += 1
        self.output.info(f"[cronolog] install wrapper patched {patched} Makefiles")
        autotools = Autotools(self)
        # NOTE: build() configures with --prefix=<package_folder> directly
        # (this vintage 1.6.2 configure predates --build/--host triplet support
        # and VAR=VALUE positional args, so the standard autotools.configure()
        # helper cannot be used). Therefore install MUST run as plain
        # `make install` WITHOUT DESTDIR: Autotools.install() injects
        # DESTDIR=<package_folder> by default, which would nest files to
        # <package_folder>/<package_folder>/sbin and leave top-level bin/sbin
        # empty (preflight 2026-09-10: package bin/sbin list failed with
        # ENOENT, cronolog binary not found). autotools.make(target=...)
        # adds no DESTDIR, matching the manual --prefix above.
        autotools.make(target="install", args=["-j1"])
        # Record exactly what `make install` staged: the 2026-09-10 preflights
        # showed top-level bin/ empty and sbin/ missing, so dump the staged
        # tree (capped) for the next diagnosis round.
        staged = []
        for root, _dirs, files in os.walk(self.package_folder):
            for name in files:
                staged.append(
                    os.path.relpath(os.path.join(root, name), self.package_folder)
                )
                if len(staged) > 500:
                    break
            if len(staged) > 500:
                break
        for entry in sorted(staged)[:100]:
            self.output.info(f"[cronolog] staged: {entry}")
        self.output.info(f"[cronolog] staged file count: {len(staged)}")
        # Locate the built binary anywhere under the package folder: expected
        # at sbin/cronolog (vintage sbin_PROGRAMS), but fall back to a
        # recursive search (e.g. a DESTDIR injected by helper/env would nest
        # it deeper). Fail loudly with the staged tree above if absent.
        cronolog_bin = None
        for root, _dirs, files in os.walk(self.package_folder):
            if "cronolog" in files:
                cand = os.path.join(root, "cronolog")
                # Exact filename match: only the compiled binary is named
                # `cronolog` (man page is cronolog.1m, info is cronolog.info).
                # Do not require +x here: fix it up best-effort below, since
                # the HMBS target may lack chmod capability.
                if os.path.isfile(cand):
                    cronolog_bin = cand
                    break
        if cronolog_bin is None:
            # `make install` staged docs but no sbin/ in all 2026-09-10
            # preflights: fall back to the just-built tree (src/cronolog was
            # linked moments ago in build()) and stage it — plus the
            # generated cronosplit script — directly instead of failing.
            self.output.warning(
                "[cronolog] binary absent from staged tree; "
                "falling back to build-tree copy"
            )
            build_cands = []
            for search_root in (self.build_folder,):
                if not search_root or not os.path.isdir(search_root):
                    continue
                for root, _dirs, files in os.walk(search_root):
                    if "cronolog" in files:
                        cand = os.path.join(root, "cronolog")
                        if os.path.isfile(cand):
                            build_cands.append(cand)
                    if len(build_cands) >= 10:
                        break
            build_cands.sort(
                key=lambda p: (
                    0 if p.replace("\\", "/").endswith("src/cronolog") else 1,
                    len(p),
                )
            )
            self.output.info(f"[cronolog] build-tree candidates: {build_cands[:5]}")
            if build_cands:
                pkg_bin = os.path.join(self.package_folder, "bin")
                os.makedirs(pkg_bin, exist_ok=True)
                dst_bin = os.path.join(pkg_bin, "cronolog")
                shutil.copyfile(build_cands[0], dst_bin)
                self.output.info(
                    f"[cronolog] build-tree copy: {build_cands[0]} -> {dst_bin}"
                )
                cronolog_bin = dst_bin
                # Stage the generated cronosplit helper next to the binary
                # (prefer the configured build-tree copy with the probed
                # perl path over the stale shipped one).
                for search_root in (self.build_folder, self.source_folder):
                    if not search_root or not os.path.isdir(search_root):
                        continue
                    found_split = None
                    for root, _dirs, files in os.walk(search_root):
                        if "cronosplit" in files:
                            cand = os.path.join(root, "cronosplit")
                            if os.path.isfile(cand):
                                found_split = cand
                                break
                    if found_split:
                        dst_split = os.path.join(pkg_bin, "cronosplit")
                        if not os.path.isfile(dst_split):
                            shutil.copyfile(found_split, dst_split)
                            self.output.info(
                                f"[cronolog] staged cronosplit: {found_split}"
                            )
                        try:
                            os.chmod(dst_split, 0o755)
                        except OSError as exc:
                            self.output.warning(
                                f"[cronolog] chmod cronosplit failed: {exc}"
                            )
                        break
            else:
                raise ConanException(
                    "cronolog binary missing after make install "
                    f"(staged {len(staged)} files, see [cronolog] staged log above)"
                )
        self.output.info(f"[cronolog] staged binary: {cronolog_bin}")
        # Normalise into bin/ so consumers find `cronolog` on the conanrun
        # PATH via bindirs=["bin"].
        pkg_bin = os.path.join(self.package_folder, "bin")
        os.makedirs(pkg_bin, exist_ok=True)
        dst_bin = os.path.join(pkg_bin, "cronolog")
        if os.path.abspath(cronolog_bin) != os.path.abspath(dst_bin):
            if os.path.exists(dst_bin):
                os.remove(dst_bin)
            shutil.move(cronolog_bin, dst_bin)
            # Prune the source dir if the move left it empty (e.g. sbin/).
            src_dir = os.path.dirname(cronolog_bin)
            try:
                if not os.listdir(src_dir):
                    os.rmdir(src_dir)
            except OSError:
                pass
        # Ensure executability (best effort: the target may lack chmod).
        try:
            os.chmod(dst_bin, 0o755)
        except OSError as exc:
            self.output.warning(f"[cronolog] chmod 755 failed: {exc}")
        # Stage the upstream test harness (noinst_PROGRAMS=cronotest): `make`
        # builds src/cronotest but `make install` never installs it, so the
        # test_package upstream test needs it staged explicitly. Prefer the
        # build-tree binary (src/cronotest), fall back to a recursive search.
        # Missing harness is a warning here; test_package fails loudly with
        # the exact search result so the next preflight log stays diagnosable.
        cronotest_src = None
        for search_root in (self.build_folder, self.source_folder):
            if not search_root or not os.path.isdir(search_root):
                continue
            direct = os.path.join(search_root, "src", "cronotest")
            if os.path.isfile(direct):
                cronotest_src = direct
                break
        if cronotest_src is None:
            for search_root in (self.build_folder, self.source_folder):
                if not search_root or not os.path.isdir(search_root):
                    continue
                for root, _dirs, files in os.walk(search_root):
                    if "cronotest" in files:
                        cand = os.path.join(root, "cronotest")
                        if os.path.isfile(cand):
                            cronotest_src = cand
                            break
                if cronotest_src:
                    break
        self.output.info(f"[cronolog] cronotest source: {cronotest_src}")
        if cronotest_src:
            dst_test = os.path.join(pkg_bin, "cronotest")
            try:
                shutil.copyfile(cronotest_src, dst_test)
                self.output.info(
                    f"[cronolog] staged cronotest: {cronotest_src} -> {dst_test}"
                )
            except OSError as exc:
                self.output.warning(f"[cronolog] copy cronotest failed: {exc}")
            try:
                os.chmod(dst_test, 0o755)
            except OSError as exc:
                self.output.warning(f"[cronolog] chmod cronotest failed: {exc}")
        else:
            self.output.warning(
                "[cronolog] cronotest harness not found in build/source tree; "
                "test_package upstream test will report it"
            )

    def package_info(self):
        # Standalone binary, no library to link against.
        # Vintage sbin_PROGRAMS: binary is normalised to bin/ in package(),
        # but keep sbin on the run path as fallback so consumers find it
        # even if the merge was skipped.
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin", "sbin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
