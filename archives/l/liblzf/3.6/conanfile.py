#!/usr/bin/env python3
"""Conan recipe — liblzf 3.6 (Autotools C library + lzf CLI tool).

liblzf (Marc Alexander Lehmann) is a tiny, extremely fast LZF (Lempel-Ziv-Free)
compression library. Upstream ships a pre-generated configure script plus a
hand-written Makefile.in that builds a static liblzf.a and the lzf(1) CLI.
Upstream has no test suite: no tests/ directory, no check/test target in
Makefile.in, so build() does not run `make check` (audited, see
test_package/MANIFEST.yml upstream_test_audit; HMBS_UPSTREAM_TEST_RESULT
status=no_tests is emitted by test_package every run).

OHOS adaptations:
    - Do not pass --build/--host (R15); the package carries no
      config.guess/config.sub and probes no host triplet.
    - Build-scope env fix (SHELL/CONFIG_SHELL/TMPDIR/compiler): the repo
      profile pins CONFIG_SHELL/SHELL to /data/service/hnp/bin/bash, which is
      not executable on some HMBS hosts, and /tmp is read-only on OHOS. A
      generated build-scope env script (wins over profile [buildenv]) plus a
      compiler fallback (keep profile clang when the file exists, else search
      PATH/SDK dirs, isfile probing only per R49) keeps configure/conftest
      working everywhere. Same pattern as the merged bwm/0.6.3 recipe.
    - Static-only by upstream design (liblzf.a, no .so), so no R26 system
      library pollution is possible.
    - Upstream Makefile.in honours neither DESTDIR nor ${prefix}/bin style
      staging, so package() installs with explicit prefix overrides
      (prefix/bindir/libdir/includedir) pointed into the package folder.
      Only bin/lzf, include/lzf.h and lib/liblzf.a are installed.
    - HMDFS/E011 + unsafe_local_mktemp: relax umask 077->022 in configure
      / config.status and shadow mktemp for ./conf* during configure only
      (zzuf/cxxtools/cyrus-sasl-login precedent) so config.status temp
      dirs stay writable.
    - HMBS install shim rejects `install -c -d` with Error 64 (EX_USAGE):
      package() installs through a recipe-local cp/mkdir shim overriding
      INSTALL (xeyes/adms precedent) so `make install` works on device.
"""

import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import get
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class LiblzfConan(ConanFile):
    name = "liblzf"
    version = "3.6"
    description = (
        "liblzf — extremely fast LZF data compression library "
        "with the lzf(1) compression CLI tool."
    )
    license = "BSD-2-Clause OR GPL-2.0-or-later"
    homepage = "http://software.schmorp.de/pkg/liblzf.html"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # Static-only by upstream design (liblzf.a, no .so): static-library
    # so Conan does not require a shared option (conan 2.x: package_type
    # "library" without a shared option fails dependency-graph computation).
    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"

    exports_sources = "conandata.yml"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.name} is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)
        # In-source autotools: configure + Makefile live in the source dir.
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R15: never pass --build/--host; liblzf probes no host triplet
        # (no config.guess/config.sub in the tarball).
        tc.configure_args = [
            a for a in tc.configure_args
            if not str(a).startswith("--build=") and not str(a).startswith("--host=")
        ]
        tc.generate()
        # Build-scope env fix (same pattern as merged bwm/0.6.3): generated
        # scripts win over the repo profile [buildenv], which pins an
        # HNP bash that is not executable on some HMBS hosts. Prefer a
        # usable shell, a writable TMPDIR (OHOS /tmp is read-only) and a
        # compiler binary that really exists on this host.
        shell = self._usable_shell()
        tmpdir = self._usable_tmpdir(makedirs=True)
        env = Environment()
        env.define("SHELL", shell)
        env.define("CONFIG_SHELL", shell)
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)
        env.define("TEMP", tmpdir)
        cc, cxx, label = self._resolve_compiler()
        if cc:
            env.define("CC", cc)
        if cxx:
            env.define("CXX", cxx)
        env.vars(self, scope="build").save_script("liblzf_hmos_fix")
        self.output.info(
            f"liblzf_hmos_fix: SHELL/CONFIG_SHELL={shell} TMPDIR={tmpdir} "
            f"compiler={label} CC={cc} CXX={cxx}"
        )

    def build(self):
        # Upstream has no test suite (audited: no tests/ dir, no check/test
        # target in the hand-written Makefile.in — see test_package/
        # MANIFEST.yml upstream_test_audit). build() therefore does NOT
        # invoke make check (upstream_test_in_build: false); the
        # HMBS_UPSTREAM_TEST_RESULT status=no_tests evidence is produced
        # by test_package every run.
        #
        # Explicit shell invocation (not Autotools.configure()/make()): the
        # helper re-exports the profile's stale CONFIG_SHELL via
        # env="conanbuild" after our override. Inline exports run after
        # conanbuild.sh is sourced, so the good values win in the same
        # shell invocation. Same pattern as the merged bwm/0.6.3 recipe.
        shell = self._usable_shell()
        tmpdir = self._usable_tmpdir(makedirs=True)
        fix = (
            f'export SHELL="{shell}" && export CONFIG_SHELL="{shell}" && '
            f'export TMPDIR="{tmpdir}" && export TMP="{tmpdir}" && export TEMP="{tmpdir}" && '
        )
        cc, cxx, label = self._resolve_compiler()
        if cc:
            fix += f'export CC="{cc}" && '
            os.environ["CC"] = cc
        if cxx:
            fix += f'export CXX="{cxx}" && '
            os.environ["CXX"] = cxx
        self.output.info(f"liblzf build shell={shell} tmpdir={tmpdir} compiler={label} CC={cc} CXX={cxx}")
        # configure ships pre-generated in the tarball (no autoreconf, no
        # autotools/perl tool_requires); the build is in-source.
        cfg_dir = self.source_folder
        if not os.path.isfile(os.path.join(cfg_dir, "configure")):
            raise ConanInvalidConfiguration(
                f"liblzf sources in {cfg_dir} contain no configure script"
            )
        # E011 (HMDFS setgid + umask 077 -> drwx--S--- owner-unwritable,
        # config.status "can't create ./conf*/...: Permission denied") plus
        # HMBS [unsafe_local_mktemp]: mktemp -d dirs on this FS cannot be
        # written by later config.status steps. Relax umask in the
        # generated script (platform adaptation, zzuf/cxxtools precedent)
        # and, when HMBS_AUTOCONF_MKTEMP_FALLBACK=1, shadow mktemp during
        # the configure phase only so Autoconf takes its mkdir fallback.
        self._patch_autoconf_umask(os.path.join(cfg_dir, "configure"))
        shim_dir = self._mktemp_fallback_shim(tmpdir)
        shim_prefix = f'export PATH="{shim_dir}:$PATH" && ' if shim_dir else ""
        try:
            # --srcdir=. (lcrq/0.3.1 precedent, 25 repo precedents): in-source
            # build so srcdir is constant; skips configure's fork-heavy
            # (expr/sed) srcdir auto-probing which fails first under
            # true-device fork/OOM pressure (/bin/sh: Out of memory).
            # umask 022 prefix keeps the mkdir-fallback temp dir writable.
            self.run(fix + shim_prefix + f'umask 022 && "{shell}" ./configure --srcdir=. --prefix=/', cwd=cfg_dir, env="conanbuild")
        except Exception:
            self._dump_config_log(cfg_dir)
            raise
        # Generated config.status carries its own hardcoded umask 077 copy;
        # relax it as well so its temp dir stays writable on HMDFS.
        self._patch_autoconf_umask(os.path.join(cfg_dir, "config.status"))
        if not os.path.isfile(os.path.join(cfg_dir, "Makefile")) and os.path.isfile(os.path.join(cfg_dir, "config.status")):
            self.output.warning("liblzf: Makefile missing after configure; retrying ./config.status once")
            retry = fix + shim_prefix + f'umask 022 && "{shell}" ./config.status'
            self.run(retry, cwd=cfg_dir, env="conanbuild")
        # R9: -j1 parallel constraint on the OHOS worker (no mktemp shim
        # here: fallback is configure-phase only per HMBS diagnosis).
        self.run(fix + "umask 022 && make -j1", cwd=cfg_dir, env="conanbuild")
        # Sanity: the two upstream artefacts must exist after make.
        for artefact in ("liblzf.a", "lzf"):
            if not os.path.isfile(os.path.join(cfg_dir, artefact)):
                raise ConanInvalidConfiguration(
                    f"liblzf build produced no {artefact} in {cfg_dir}"
                )

    def _patch_autoconf_umask(self, path):
        # E011/HMDFS: autoconf template `umask 077 && mktemp -d
        # "./confXXXXXX"` yields an owner-unwritable dir on HMDFS
        # (0700 + setgid -> drwx--S---), so config.status fails with
        # "can't create ./conf*/...: Permission denied". Rewrite to
        # umask 022 (platform adaptation, zzuf/cxxtools precedent).
        try:
            with open(path, "r", encoding="utf-8", errors="surrogateescape") as handle:
                content = handle.read()
        except OSError:
            return
        if "umask 077" not in content:
            return
        content = content.replace("umask 077", "umask 022")
        try:
            with open(path, "w", encoding="utf-8", errors="surrogateescape", newline="\n") as handle:
                handle.write(content)
        except OSError:
            return
        self.output.info(f"liblzf: relaxed umask 077->022 in {os.path.basename(path)}")

    def _mktemp_fallback_shim(self, tmpdir):
        # HMBS [unsafe_local_mktemp]: a directory created by mktemp on the
        # current device FS cannot be written by later config.status steps.
        # When HMBS_AUTOCONF_MKTEMP_FALLBACK=1, shadow mktemp during the
        # configure step only so calls for "./conf*" fail and Autoconf
        # falls back to its `mkdir` path (cyrus-sasl-login precedent). All
        # other mktemp calls delegate to the real binary; TMPDIR itself
        # stays writable.
        if os.environ.get("HMBS_AUTOCONF_MKTEMP_FALLBACK") != "1":
            return ""
        shim_dir = os.path.join(tmpdir, "hmbs-mktemp-shim")
        try:
            os.makedirs(shim_dir, exist_ok=True)
        except OSError:
            return ""
        real = (shutil.which("mktemp") or "/bin/mktemp").replace('"', "")
        shim = os.path.join(shim_dir, "mktemp")
        script = (
            "#!/bin/sh\n"
            'for arg in "$@"; do\n'
            '  case "$arg" in\n'
            "    *conf*) exit 1 ;;\n"
            "  esac\n"
            "done\n"
            'for candidate in /bin/mktemp /usr/bin/mktemp; do\n'
            '  if [ -x "$candidate" ]; then\n'
            '    exec "$candidate" "$@"\n'
            "  fi\n"
            "done\n"
            f'exec "{real}" "$@"\n'
        )
        try:
            with open(shim, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(script)
            try:
                os.chmod(shim, 0o755)
            except OSError:
                pass
        except OSError:
            return ""
        self.output.info(f"liblzf: mktemp fallback shim active for configure: {shim_dir}")
        return shim_dir

    def _dump_config_log(self, cfg_dir):
        try:
            log = os.path.join(cfg_dir, "config.log")
            if not os.path.isfile(log):
                self.output.warning("liblzf: config.log not found after configure failure")
                return
            with open(log, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
            self.output.info("liblzf config.log tail (last 12k):\n" + text[-12000:])
            m = re.search(r"(checking whether the C compiler works.*)", text, re.S)
            if m:
                self.output.info("liblzf config.log compiler section:\n" + m.group(1)[:8000])
        except Exception as e:
            self.output.warning(f"liblzf: dump config.log failed: {e}")

    def _usable_shell(self):
        # HMBS guarantees shell=/bin/sh; the repo profile pins HNP bash
        # which is not executable on some HMBS hosts. Hard-prefer /bin/sh
        # and never return the HNP path, even if isfile() is true for it.
        if os.path.isfile("/bin/sh"):
            return "/bin/sh"
        sh_which = shutil.which("sh") or ""
        if sh_which and os.path.isfile(sh_which):
            return sh_which
        for cand in (os.environ.get("SHELL", ""), os.environ.get("CONFIG_SHELL", "")):
            if not cand:
                continue
            first = cand.split()[0]
            if "hnp/bin/bash" in first:
                continue
            if os.path.isfile(first):
                return cand
        return "/bin/sh"

    def _usable_tmpdir(self, makedirs=False):
        # Priority: HMBS task-local TMPDIR/TMP/TEMP (injected writable);
        # never fall back to /tmp (read-only on OHOS); else build-local tmp.
        for var in ("TMPDIR", "TMP", "TEMP"):
            cand = os.environ.get(var, "")
            if cand and cand != "/tmp" and os.path.isdir(cand):
                return cand
        tmpd = os.path.join(self.build_folder, "tmp")
        if makedirs:
            os.makedirs(tmpd, exist_ok=True)
        return tmpd

    def _resolve_compiler(self):
        """Return (cc, cxx, label) for a compiler that exists on this host.

        Keep the profile tools.build:compiler_executables value when the
        file exists (CI worker unchanged); otherwise search PATH plus
        SDK/harmonybrew candidate dirs. Pure isfile probing, no X_OK
        probing per R49.
        """
        def _ok(p):
            try:
                return bool(p) and os.path.isfile(p)
            except Exception:
                return False

        def _conf(key):
            try:
                return (self.conf.get(key, check_type=str) or "").split()[0]
            except Exception:
                return ""

        conf_cc = _conf("tools.build:compiler_executables:c")
        conf_cxx = _conf("tools.build:compiler_executables:cpp")
        if _ok(conf_cc) and _ok(conf_cxx):
            return conf_cc, conf_cxx, "profile"
        if _ok(conf_cc) and not conf_cxx:
            sib = conf_cc + "++" if conf_cc.endswith("clang") else ""
            if _ok(sib):
                return conf_cc, sib, "profile-cxx-sibling"

        cc_names = ["clang", "cc", "gcc"]
        cxx_names = ["clang++"]
        cand_dirs = [
            "/storage/Users/currentUser/usr/local/bin",
            os.path.join(os.path.expanduser("~"), ".harmonybrew", "bin"),
            "/data/service/hnp/bin",
            "/opt/llvm/bin",
            "/usr/local/bin",
            "/usr/bin",
        ]
        try:
            for entry in (os.environ.get("LD_LIBRARY_PATH", "") or "").split(os.pathsep):
                if "llvm" in entry:
                    sib = os.path.join(os.path.dirname(entry.rstrip("/")), "bin")
                    if sib not in cand_dirs:
                        cand_dirs.append(sib)
        except Exception:
            pass

        found_cc, found_cxx = "", ""
        for name in cc_names:
            w = shutil.which(name)
            if _ok(w):
                found_cc = w
                break
        for name in cxx_names:
            w = shutil.which(name)
            if _ok(w):
                found_cxx = w
                break
        if not found_cc or not found_cxx:
            for d in cand_dirs:
                try:
                    if not os.path.isdir(d):
                        continue
                except Exception:
                    continue
                if not found_cc:
                    for n in cc_names:
                        p = os.path.join(d, n)
                        if _ok(p):
                            found_cc = p
                            break
                if not found_cxx:
                    for n in cxx_names:
                        p = os.path.join(d, n)
                        if _ok(p):
                            found_cxx = p
                            break
                if found_cc and found_cxx:
                    break
        cc = found_cc or (conf_cc if _ok(conf_cc) else "")
        cxx = found_cxx or (conf_cxx if _ok(conf_cxx) else "")
        if cc and not cxx and cc.endswith("clang"):
            sib = cc + "++"
            if _ok(sib):
                cxx = sib
        if cc:
            return cc, cxx, "fallback"
        return "", "", "unresolved"

    def _write_install_shim(self):
        # HMBS install shim (runtime/<task>/bin/install, install_shim:true)
        # only accepts single-file two-arg calls (`[ $# -eq 2 ] || exit 64`)
        # so `install -c -d <dir>` and multi-source copies fail with Error 64
        # (xeyes 1.3.1 / adms 2.3.7 / lzop 1.04 precedent). Write a cp/mkdir
        # shim handling -p/-c/-m/-d/-- plus single and multi source copies
        # (mkdir -p semantics, chmod || true for HMBS_CAP_CHMOD=0) and point
        # INSTALL at it. HMFS grants exec from open mode (chmod cap is 0):
        # use os.open 0o755 so the shim is directly executable.
        shim_dir = os.path.join(self.build_folder, "_ohos_install_shim")
        os.makedirs(shim_dir, exist_ok=True)
        install = os.path.join(shim_dir, "install")
        fd = os.open(install, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o755)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
                f.write(
                    "#!/bin/sh\n"
                    "set -eu\n"
                    "mode=\n"
                    "while [ $# -gt 0 ]; do\n"
                    "  case \"$1\" in\n"
                    "    -p|-c) shift ;;\n"
                    "    -m) [ $# -ge 2 ] || exit 2; mode=$2; shift 2 ;;\n"
                    "    -d) shift; [ $# -gt 0 ] || exit 2; mkdir -p \"$@\"; exit 0 ;;\n"
                    "    --) shift; break ;;\n"
                    "    -*) shift ;;\n"
                    "    *) break ;;\n"
                    "  esac\n"
                    "done\n"
                    "[ $# -ge 2 ] || exit 2\n"
                    "dest=\n"
                    "for arg in \"$@\"; do dest=$arg; done\n"
                    "count=$(($# - 1))\n"
                    "if [ \"$count\" -gt 1 ]; then\n"
                    "  mkdir -p \"$dest\"\n"
                    "else\n"
                    "  mkdir -p \"$(dirname \"$dest\")\"\n"
                    "fi\n"
                    "i=1\n"
                    "for src in \"$@\"; do\n"
                    "  [ $i -gt $count ] && break\n"
                    "  cp -f \"$src\" \"$dest\"\n"
                    "  if [ -n \"$mode\" ]; then\n"
                    "    if [ -d \"$dest\" ]; then chmod \"$mode\" \"$dest/${src##*/}\" 2>/dev/null || true\n"
                    "    else chmod \"$mode\" \"$dest\" 2>/dev/null || true; fi\n"
                    "  fi\n"
                    "  i=$((i + 1))\n"
                    "done\n"
                )
        except Exception:
            try:
                os.close(fd)
            except Exception:
                pass
            raise
        try:
            os.chmod(install, 0o755)
        except OSError:
            pass  # HMBS_CAP_CHMOD=0: HMFS ignores chmod
        self.output.info(f"liblzf: install shim ready at {install}")
        return install

    def package(self):
        # Upstream Makefile.in honours no DESTDIR: install paths come
        # straight from $(bindir)/$(libdir)/$(includedir). Install with
        # explicit prefix overrides pointed into the package folder so no
        # file ever lands outside it. Only bin/lzf, include/lzf.h and
        # lib/liblzf.a are installed upstream.
        #
        # HMBS install shim (runtime/<task>/bin/install, install_shim:true)
        # only accepts single-file two-arg calls and rejects `install -c -d`
        # with Error 64 (EX_USAGE). Override INSTALL with a recipe-local
        # cp/mkdir shim (xeyes/adms precedent) plus a PATH shadow so both
        # $(INSTALL) and bare `install` invocations work on device.
        pkg = self.package_folder
        shim_install = self._write_install_shim()
        shim_dir = os.path.dirname(shim_install)
        self.run(
            f'umask 022 && export PATH="{shim_dir}:$PATH" && '
            f"make install prefix=\"{pkg}\" exec_prefix=\"{pkg}\" "
            f"bindir=\"{pkg}/bin\" libdir=\"{pkg}/lib\" includedir=\"{pkg}/include\" "
            f"INSTALL=\"{shim_install}\"",
            cwd=self.source_folder,
            env="conanbuild",
        )
        for artefakt in ("bin/lzf", "include/lzf.h", "lib/liblzf.a"):
            path = os.path.join(pkg, artefakt)
            if not os.path.isfile(path):
                raise ConanInvalidConfiguration(
                    f"liblzf package missing expected file: {artefakt}"
                )
        try:
            os.chmod(os.path.join(pkg, "bin", "lzf"), 0o755)
        except OSError:
            pass

    def package_info(self):
        self.cpp_info.libs = ["lzf"]
        # bin/lzf is a real installed CLI (L0k/R38: tool declaration).
        self.cpp_info.bindirs = ["bin"]
