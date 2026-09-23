#!/usr/bin/env python3
"""Conan recipe — xqilla 2.3.4 (Autotools, XQuery/XPath 2 library + CLI).

XQilla is an XQuery and XPath 2.0 library and command line utility written
in C++, implemented on top of the Xerces-C++ XML parser library.

HarmonyOS PC (aarch64) notes:
    * W0: single published in-tree dependency — xerces-c/3.2.5 (pinned
      to the ohpcd in-repo RREV so preflight, which resolves conancenter
      first, stays on the hardened in-repo recipe; libe57format precedent).
    * configure takes --with-xerces=<xerces package_folder> explicitly;
      no system prefix lookup, no pkg-config bridging needed.
    * CXXFLAGS pins -std=c++14: upstream uses the `register` storage
      specifier (removed in C++17, still accepted in C++14); nixpkgs and
      Homebrew carry the same requirement (ENV.cxx11 / CXXFLAGS=-std=c++14).
    * Upstream ships no automated `make check` suite (audited in
      test_package/MANIFEST.yml: tests/ holds two manual runners needing
      external datasets, Makefile.am has no check target); build() guards
      this so the no_tests audit cannot silently go stale.
    * HMBS hardening: writable TMPDIR probe (read-only /tmp), /bin/sh as
      CONFIG_SHELL/SHELL, single-job make for the worker constraint.
"""

import os
import shutil
import stat
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import load_toolchain_args
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rm
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


def _pick_writable_tmp(build_folder):
    """Pick a truly writable TMPDIR (coinor-vol/1.5.4 lesson).

    Probes with a real makedirs + open(w) + unlink instead of trusting
    isdir alone; falls back to build_folder/tmp (conan has materialised
    sources there, writable on both device and CI workers).
    """
    try:
        fb = build_folder or os.getcwd()
    except Exception:
        fb = os.getcwd()
    candidates = []
    for key in ("HMBS_TMPDIR", "TMPDIR", "TMP", "TEMP",
                "HMBS_AUTOCONF_MKTEMP_FALLBACK"):
        val = os.environ.get(key)
        if val:
            candidates.append(val)
    candidates.append(os.path.join(fb, "tmp"))
    for cand in candidates:
        try:
            old = os.umask(0o022)
            try:
                os.makedirs(cand, exist_ok=True)
            finally:
                os.umask(old)
            probe = os.path.join(cand, ".hmbs_write_probe")
            with open(probe, "w", encoding="utf-8") as pf:
                pf.write("ok")
            try:
                os.remove(probe)
            except OSError:
                pass
            return cand
        except OSError:
            continue
    fallback = os.path.join(fb, "tmp")
    try:
        os.makedirs(fallback, exist_ok=True)
    except OSError:
        pass
    return fallback


class XqillaConan(ConanFile):
    name = "xqilla"
    version = "2.3.4"
    description = "XQuery and XPath 2.0 library and command line utility on top of Xerces-C"
    license = "Apache-2.0"
    homepage = "https://xqilla.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("xquery", "xpath", "xml", "xerces")
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("xerces-c/3.2.5#9086fe3ffea711440f8f71d66d6ca6d0")

    def layout(self):
        basic_layout(self)

    def source(self):
        tmp = _pick_writable_tmp(self.base_source_folder if hasattr(self, "base_source_folder") else self.build_folder)
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = tmp
        get(self, **self.conan_data["sources"], strip_root=True)

    def _ohos_compilers_from_conf(self):
        """OHOS compiler resolution: conf first, PATH/env fallback.

        Primary source remains tools.build:compiler_executables from the
        ohos-aarch64 profile / HMBS preflight. The 2026-09-20 preflight
        showed CC=None CXX=None here (conf not propagated to this
        context, or the pinned /data/service/hnp path absent), which
        previously hard-failed the build. Fallback chain (isfile check
        only — on HMFS os.access(X_OK) is always False, E046):
        conf -> $CC/$CXX env -> PATH clang/clang++ -> well-known HNP
        paths -> cc/c++. Returns (None, None) only if nothing found.
        """
        try:
            compilers = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
        except Exception:
            compilers = {}
        cc = compilers.get("c")
        cxx = compilers.get("cpp")

        def _valid(path):
            try:
                return bool(path) and os.path.isfile(path)
            except Exception:
                return False

        if not _valid(cc):
            cc = None
        if not _valid(cxx):
            cxx = None
        if cc and cxx:
            return cc, cxx
        # Env fallback (HMBS or caller may export CC/CXX directly).
        if not cc:
            env_cc = os.environ.get("CC", "").strip().split()[0] if os.environ.get("CC") else None
            if _valid(env_cc):
                cc = env_cc
        if not cxx:
            env_cxx = os.environ.get("CXX", "").strip().split()[0] if os.environ.get("CXX") else None
            if _valid(env_cxx):
                cxx = env_cxx
        # PATH fallback: HMBS pre-pends the toolchain dir to PATH, so
        # plain which() finds the OHOS clang even when conf is missing.
        if not cc:
            found = shutil.which("clang") or shutil.which("cc") or shutil.which("gcc")
            if _valid(found):
                cc = found
        if not cxx:
            found = shutil.which("clang++") or shutil.which("c++") or shutil.which("g++")
            if _valid(found):
                cxx = found
        # Well-known HNP locations (profile default + common variants).
        for cand in ("/data/service/hnp/bin/clang",
                     "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/clang"):
            if not cc and _valid(cand):
                cc = cand
                break
        for cand in ("/data/service/hnp/bin/clang++",
                     "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/clang++"):
            if not cxx and _valid(cand):
                cxx = cand
                break
        # Sibling derivation: clang and clang++ always ship together.
        if cc and not cxx:
            sib = os.path.join(os.path.dirname(cc), "clang++")
            if _valid(sib):
                cxx = sib
        if cxx and not cc:
            sib = os.path.join(os.path.dirname(cxx), "clang")
            if _valid(sib):
                cc = sib
        return cc, cxx

    def _ensure_ohos_compiler_env(self):
        """Export the conf compilers + toolchain PATH for configure/make.

        Distinct from probe-and-pin precedents: no candidate list, no
        version/compile probes. Derives the toolchain dir from the
        conf compiler dirname only (xeyes precedent) so clang's
        internal ld.lld/as lookup succeeds, then pins
        CC/CXX/CPP/CXXCPP deterministically in os.environ for both
        the configure invocation and the subsequent make.
        """
        if str(self.settings.os) != "OHOS":
            return
        cc, cxx = self._ohos_compilers_from_conf()
        for tool in (cc, cxx):
            if not tool:
                continue
            toolchain_dir = os.path.dirname(tool)
            if not toolchain_dir:
                continue
            cur = os.environ.get("PATH", "")
            parts = cur.split(os.pathsep) if cur else []
            if toolchain_dir not in parts:
                os.environ["PATH"] = toolchain_dir + os.pathsep + cur if cur else toolchain_dir
        if cc:
            os.environ["CC"] = cc
            os.environ["CPP"] = cc + " -E"
        if cxx:
            os.environ["CXX"] = cxx
            os.environ["CXXCPP"] = cxx + " -E"
        self.output.info(
            "xqilla OHOS compiler env: CC={} CXX={}".format(
                os.environ.get("CC"), os.environ.get("CXX")))

    def _dump_config_log(self):
        """Emit the diagnostic section of config.log, not just the tail.

        Previous round dumped only the last 80 lines (variable dump +
        confdefs.h), hiding the actual compiler probe failure in the
        middle of the file. Now extracts: env assignments (CC/CXX/
        CFLAGS/CXXFLAGS/CPPFLAGS/LDFLAGS), the C++ probe block, the
        failed conftest program, and any error/cannot lines, plus 6
        lines of context around 'cannot create executables'.
        Searches build_folder, build-release/ and build/. Never raises.
        """
        candidates = [
            os.path.join(self.build_folder, "config.log"),
            os.path.join(self.build_folder, "build-release", "config.log"),
            os.path.join(self.build_folder, "build", "config.log"),
        ]
        target = None
        for path in candidates:
            try:
                if path and os.path.isfile(path):
                    target = path
                    break
            except Exception:
                continue
        if target is None:
            try:
                for root, _dirs, files in os.walk(self.build_folder):
                    if "config.log" in files:
                        target = os.path.join(root, "config.log")
                        break
            except Exception:
                target = None
        if target is None:
            self.output.warning(
                "xqilla configure failed and no config.log was found "
                "(searched build_folder, build-release/, build/)")
            return
        try:
            with open(target, encoding="utf-8", errors="replace") as handle:
                lines = handle.read().splitlines()
        except OSError as exc:
            self.output.warning("cannot read config.log: {}".format(exc))
            return
        self.output.error("---- config.log: {} ({} lines, diagnostic excerpt) ----".format(target, len(lines)))
        import re
        env_pat = re.compile(r"^(CC|CXX|CPP|CXXCPP|CFLAGS|CXXFLAGS|CPPFLAGS|LDFLAGS|PATH|TMPDIR|CONFIG_SHELL|SHELL)=")
        probe_pat = re.compile(r"checking for C\+\+ compiler|C\+\+ compiler cannot|failed program|conftest|error:|cannot create|no acceptable|not found|unable to", re.IGNORECASE)
        hit_idx = [i for i, l in enumerate(lines) if "cannot create executables" in l]
        keep = set()
        for i, line in enumerate(lines):
            if env_pat.match(line) or probe_pat.search(line):
                for j in range(max(0, i - 2), min(len(lines), i + 7)):
                    keep.add(j)
        for i in hit_idx:
            for j in range(max(0, i - 25), min(len(lines), i + 10)):
                keep.add(j)
        if not keep:
            # Fallback: middle of the file where the probe lives, not the tail dump.
            for j in range(max(0, len(lines) - 400), len(lines) - 80):
                keep.add(j)
        for i in sorted(keep)[:220]:
            self.output.error(lines[i])
        self.output.error("---- end config.log excerpt ----")

    def generate(self):
        tmp = _pick_writable_tmp(self.build_folder)
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = tmp
        self.buildenv.define("CONFIG_SHELL", "/bin/sh")
        self.buildenv.define("SHELL", "/bin/sh")
        self.buildenv.define_path("TMPDIR", tmp)
        self.buildenv.define_path("TMP", tmp)
        self.buildenv.define_path("TEMP", tmp)
        tc = AutotoolsToolchain(self)
        if self.settings.os == "OHOS":
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-ohos",
            ])
        xerces_folder = self.dependencies["xerces-c"].package_folder
        tc.configure_args.append("--with-xerces={}".format(xerces_folder))
        tc.configure_args.append("--disable-rpath")
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        else:
            tc.configure_args.append("--enable-shared")
        tc.extra_cxxflags.append("-std=c++14")
        tc.extra_cflags.append("-std=c11")
        if self.settings.os == "OHOS":
            # OHOS clang links C++ against libc++ (no libstdc++ on musl);
            # the C-only configure checks pass while the C++ link test
            # fails without it. test_package already builds with
            # -stdlib=libc++; mirror it here for the configure probe
            # and the library build. Duplicate -stdlib is harmless.
            tc.extra_cxxflags.append("-stdlib=libc++")
            tc.extra_ldflags.append("-stdlib=libc++")
            # 2026-09-21 preflight: single-TU SIGKILL (Signal 9, exit 137)
            # on XQillaXQCStaticContext.cpp with -O3 -ftemplate-depth-50
            # under -j1. HMBS worker is memory-constrained; -O3 template
            # inlining blows per-TU RSS and the OOM killer SIGKILLs cc1plus.
            # Append -O1 LAST so it wins over the Release default -O3 and
            # any upstream AM_CXXFLAGS -O3 (last -O wins in clang; both in
            # $(CXXFLAGS) after $(AM_CXXFLAGS)). Functional behaviour
            # unchanged for an XML query library; only codegen level drops.
            tc.extra_cflags.append("-O1")
            tc.extra_cxxflags.append("-O1")
            cc, cxx = self._ohos_compilers_from_conf()
            if cc:
                self.buildenv.define("CC", cc)
                self.buildenv.define("CPP", cc + " -E")
            if cxx:
                self.buildenv.define("CXX", cxx)
                self.buildenv.define("CXXCPP", cxx + " -E")
        tc.generate()

    def _patch_autotools_for_ohos(self):
        """Accept aarch64-unknown-linux-ohos in bundled GNU config scripts.

        XQilla 2.3.4 ships a pre-2010 config.sub that rejects the OHOS
        triplet (E072: "machine 'aarch64-unknown-linux' not recognized").
        Insert a version-agnostic fast-path right after the shebang so any
        *ohos* input canonicalises to *-unknown-linux-ohos without touching
        the fragile per-version android-linux / kernel-OS whitelist blocks.
        config.guess gets a best-effort HarmonyOS branch (E007) when the
        NetBSD anchor exists. Idempotent: re-runs skip patched files.

        Also rewrites `umask 077` -> `umask 022` in every `configure`
        script under source/build roots (E011): autoconf creates its
        ./confXXXXXX tmp dir with umask 077 (0700); on HMDFS the dir
        gains setgid (drwx--S---) via UID mapping so even the owner
        cannot write subs1.awk/subs1.sed and config.status aborts with
        "can't create ./conf*/subs1.awk: Permission denied". umask 022
        yields a writable dir (xapian-core 0004-configure.patch precedent).
        The generated config.status inherits the fixed umask because it
        is templated from the patched configure. Idempotent.
        """
        if str(self.settings.os) != "OHOS":
            return
        roots = set()
        for base in (getattr(self, "source_folder", None),
                     getattr(self, "base_source_folder", None),
                     getattr(self, "base_build_folder", None),
                     getattr(self, "build_folder", None)):
            if base and os.path.isdir(str(base)):
                roots.add(str(base))
        if not roots:
            return
        sub_marker = "OHOS fast-path (xqilla OHOS port, E007/E072)"
        sub_snippet = (
            "\n# OHOS fast-path (xqilla OHOS port, E007/E072):\n"
            "# bundled config.sub predates OHOS; canonicalise any ohos\n"
            "# triplet before the per-version validation below runs.\n"
            'case "$1" in\n'
            "  *-linux-ohos|*-ohos-linux|*-unknown-linux-ohos|*ohos*)\n"
            '    _ohos_machine=`echo "$1" | cut -d- -f1`\n'
            "    case \"$_ohos_machine\" in\n"
            "      aarch64|arm64) _ohos_machine=aarch64 ;;\n"
            "      arm*) _ohos_machine=arm ;;\n"
            "      x86_64|amd64) _ohos_machine=x86_64 ;;\n"
            "      i?86) _ohos_machine=i686 ;;\n"
            "    esac\n"
            '    echo "${_ohos_machine}-unknown-linux-ohos"\n'
            "    exit 0\n"
            "    ;;\n"
            "esac\n"
        )
        guess_block = (
            "    *:HarmonyOS:*:*)\n"
            '\tcase "$UNAME_MACHINE" in\n'
            "\t    aarch64|arm64) MACHINE=aarch64 ;;\n"
            "\t    armv7*|armv8*) MACHINE=arm ;;\n"
            "\t    x86_64|amd64)  MACHINE=x86_64 ;;\n"
            "\t    i?86)         MACHINE=i686 ;;\n"
            '\t    *)            MACHINE="$UNAME_MACHINE" ;;\n'
            "\tesac\n"
            "\tGUESS=${MACHINE}-unknown-linux-ohos\n"
            "\t;;\n\n"
        )
        patched_sub, patched_guess = 0, 0
        for root in roots:
            for dirpath, _dirnames, filenames in os.walk(root):
                for name in filenames:
                    if name not in ("config.sub", "config.guess"):
                        continue
                    path = os.path.join(dirpath, name)
                    try:
                        with open(path, "r", encoding="utf-8",
                                  errors="replace", newline="") as handle:
                            content = handle.read()
                    except OSError:
                        continue
                    if name == "config.sub":
                        if sub_marker in content:
                            continue
                        lines = content.splitlines(keepends=True)
                        if lines and lines[0].startswith("#!"):
                            lines.insert(1, sub_snippet)
                            new_content = "".join(lines)
                        else:
                            new_content = sub_snippet + content
                        try:
                            with open(path, "w", encoding="utf-8",
                                      newline="") as handle:
                                handle.write(new_content)
                            patched_sub += 1
                        except OSError:
                            continue
                    else:
                        if "HarmonyOS" in content:
                            continue
                        anchor = None
                        for cand in ("*:NetBSD:*:*)", "*:NetBSD:*:* )"):
                            if cand in content:
                                anchor = cand
                                break
                        if anchor is None:
                            continue
                        new_content = content.replace(anchor,
                                                      guess_block + anchor, 1)
                        if new_content == content:
                            continue
                        try:
                            with open(path, "w", encoding="utf-8",
                                      newline="") as handle:
                                handle.write(new_content)
                            patched_guess += 1
                        except OSError:
                            continue
        self.output.info(
            "xqilla OHOS autotools triplet patch: "
            "config.sub={}, config.guess={}".format(patched_sub, patched_guess))
        # E011: HMDFS + umask 077 -> config.status "can't create
        # ./conf*/subs1.awk: Permission denied". Rewrite every configure
        # under the same roots (version-agnostic, no line numbers).
        fixed_umask = 0
        for root in roots:
            for dirpath, _dirnames, filenames in os.walk(root):
                for name in filenames:
                    if name != "configure":
                        continue
                    path = os.path.join(dirpath, name)
                    try:
                        st = os.stat(path)
                    except OSError:
                        continue
                    try:
                        with open(path, "r", encoding="utf-8",
                                  errors="replace", newline="") as handle:
                            content = handle.read()
                    except OSError:
                        continue
                    if "umask 077" not in content:
                        continue
                    new_content = content.replace("umask 077", "umask 022")
                    try:
                        with open(path, "w", encoding="utf-8",
                                  newline="") as handle:
                            handle.write(new_content)
                    except OSError:
                        continue
                    try:
                        os.chmod(path, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
                    except OSError:
                        pass
                    fixed_umask += 1
        self.output.info(
            "xqilla OHOS autoconf umask patch (E011): configure={}".format(fixed_umask))

    def _assert_no_automated_upstream_tests(self):
        """Fail closed if upstream ever gains a check/test target.

        Audited for 2.3.4: Makefile.am has no check target (.PHONY test
        with no rule body), tests/ holds only manual runners (xmarkRunner
        needs an external benchmark config file, xqtsRunner needs the
        external W3C XQTS suite download — only errors.xml fragments
        ship in the tarball). If a future tarball adds an automated
        target, this guard forces the no_tests audit to be revisited
        instead of silently skipping it.
        """
        makefile_am = os.path.join(self.source_folder, "Makefile.am")
        targets = set()
        if os.path.isfile(makefile_am):
            with open(makefile_am, "r", encoding="utf-8", errors="replace") as handle:
                for line in handle:
                    if line and not line[0].isspace() and ":" in line:
                        lhs = line.split(":", 1)[0].strip()
                        for token in lhs.split():
                            targets.add(token)
        for forbidden in ("check", "check-am"):
            if forbidden in targets:
                raise ConanException(
                    "xqilla upstream gained a '{}' target — the no_tests "
                    "audit in test_package/MANIFEST.yml must be revisited".format(forbidden)
                )

    def _load_configure_args(self):
        try:
            return load_toolchain_args(self.generators_folder).get("configure_args", "")
        except Exception:
            return ""

    def _run_configure_direct(self, configure_args):
        """Invoke configure with inline-pinned compilers (xapian-core pattern).

        Previous round set CC/CXX via buildenv.define + os.environ and
        relied on the Autotools helper to forward them, but the
        preflight config.log still showed ac_ct_CC/ac_ct_CXX empty and
        the probe failed identically — the env never reached the
        configure process. Direct invocation puts CC/CXX/CPP/CXXCPP +
        AR/RANLIB/NM/LD + CONFIG_SHELL/SHELL on the command line, so
        propagation no longer depends on conanbuild aggregation.
        """
        cc, cxx = self._ohos_compilers_from_conf()
        if not cc or not cxx:
            raise ConanException(
                "xqilla OHOS build found no C/C++ compiler "
                "c/cpp fallback empty; got CC={} CXX={})".format(cc, cxx))
        toolchain_dir = os.path.dirname(cc)
        cur = os.environ.get("PATH", "")
        parts = cur.split(os.pathsep) if cur else []
        if toolchain_dir and toolchain_dir not in parts:
            os.environ["PATH"] = toolchain_dir + os.pathsep + cur if cur else toolchain_dir
        config_shell = "/bin/sh"
        ar = shutil.which("llvm-ar") or shutil.which("ar") or "ar"
        ranlib = shutil.which("llvm-ranlib") or shutil.which("ranlib") or "ranlib"
        nm = shutil.which("llvm-nm") or shutil.which("nm") or "nm"
        ld = shutil.which("ld.lld") or shutil.which("ld") or "ld"
        self.output.info(
            "xqilla OHOS direct configure: CC={} CXX={} AR={}".format(cc, cxx, ar))
        # NOTE: keep this self.run form stable — ci L0h greps for the
        # conf-first compiler pattern (R33); comment only, no ${CC} here.
        cmd = (
            'CC="{cc}" CXX="{cxx}" CPP="{cc} -E" CXXCPP="{cxx} -E" '
            'AR="{ar}" RANLIB="{ranlib}" NM="{nm}" LD="{ld}" '
            'CONFIG_SHELL="{sh}" SHELL="{sh}" '
            '"{sh}" "{src}/configure" {args}'
        ).format(cc=cc, cxx=cxx, ar=ar, ranlib=ranlib, nm=nm, ld=ld,
                 sh=config_shell, src=self.source_folder, args=configure_args)
        self.run(cmd, cwd=self.build_folder)
        return cc, cxx

    def build(self):
        self._assert_no_automated_upstream_tests()
        tmp = _pick_writable_tmp(self.build_folder)
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = tmp
        os.environ["SHELL"] = "/bin/sh"
        os.environ["CONFIG_SHELL"] = "/bin/sh"
        self._ensure_ohos_compiler_env()
        if str(self.settings.os) == "OHOS":
            # Belt-and-suspenders for the -O1 downgrade in generate():
            # conanbuild.sh aggregation order may vary, but os.environ
            # CXXFLAGS is expanded last on the libtool compile line
            # (after AM_CXXFLAGS), so a trailing -O1 here guarantees it
            # wins over any -O3 injected elsewhere. Idempotent append.
            for _key in ("CFLAGS", "CXXFLAGS"):
                _cur = os.environ.get(_key, "")
                if "-O1" not in _cur:
                    os.environ[_key] = (_cur + " -O1").strip()
            self.output.info("xqilla OHOS opt downgrade: CFLAGS={} CXXFLAGS={}".format(
                os.environ.get("CFLAGS"), os.environ.get("CXXFLAGS")))
        apply_conandata_patches(self)
        self._patch_autotools_for_ohos()
        if str(self.settings.os) == "OHOS":
            configure_args = self._load_configure_args()
            try:
                cc, cxx = self._run_configure_direct(configure_args)
            except ConanException:
                self._dump_config_log()
                raise
            autotools = Autotools(self)
            try:
                autotools.make(args=["-j1", "CC=" + cc, "CXX=" + cxx])
            except ConanException:
                self._dump_config_log()
                raise
            return
        autotools = Autotools(self)
        try:
            autotools.configure()
        except ConanException:
            self._dump_config_log()
            raise
        autotools.make(args=["-j1"])

    def _sign_elf(self, path):
        if str(self.settings.os) != "OHOS":
            return
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        if not os.path.isfile(signer):
            raise ConanException(
                "OHOS ELF signing requires binary-sign-tool: {}".format(path)
            )
        subprocess.run(
            [objcopy, "--remove-section", ".codesign", path],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
        )
        signed = path + ".signed"
        subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", signed, "-selfSign", "1"],
            check=True,
        )
        if os.path.isfile(signed):
            os.replace(signed, path)
        try:
            os.chmod(
                path,
                stat.S_IMODE(os.stat(path).st_mode)
                | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH,
            )
        except OSError:
            pass  # HMBS_CAP_CHMOD=0 on HMDFS user partition; open mode already set

    def _manual_install(self):
        """Stage lib + headers + CLI without /bin/install (xlslib precedent).

        True-machine preflight fails at install-nobase_includeHEADERS with
        exit 64: the HMBS sandbox masks the install(1) binary / does not
        support chmod (HMBS_CAP_CHMOD=0), so any `make install` rule that
        shells out to `install -c -m 644` cannot succeed no matter how the
        compiler is pinned. Mirror the upstream `make install` layout with
        plain shutil.copyfile data copies (no install binary, no chmod):
        include/ headers from the source tree, libxqilla archive/shared
        objects plus the xqilla CLI from the build tree. Nothing is
        skipped: the same artefacts `make install` would stage are staged.
        """
        staged_headers = 0
        for inc_root in (os.path.join(self.source_folder, "include"),):
            if not os.path.isdir(inc_root):
                continue
            for dirpath, _dirnames, filenames in os.walk(inc_root):
                for name in filenames:
                    if not (name.endswith(".h") or name.endswith(".hpp")):
                        continue
                    src_file = os.path.join(dirpath, name)
                    rel = os.path.relpath(src_file, inc_root)
                    dst_file = os.path.join(self.package_folder, "include", rel)
                    os.makedirs(os.path.dirname(dst_file), exist_ok=True)
                    shutil.copyfile(src_file, dst_file)
                    staged_headers += 1
        # Overlay configure-generated headers from the build tree, if any
        # (same relative layout; source copy wins ties by going first).
        build_inc = os.path.join(self.build_folder, "include")
        try:
            same = os.path.realpath(build_inc) == os.path.realpath(
                os.path.join(self.source_folder, "include"))
        except Exception:
            same = False
        if os.path.isdir(build_inc) and not same:
            for dirpath, _dirnames, filenames in os.walk(build_inc):
                if "autom4te" in dirpath:
                    continue
                for name in filenames:
                    if not (name.endswith(".h") or name.endswith(".hpp")):
                        continue
                    if name in ("Makefile", "Makefile.in"):
                        continue
                    src_file = os.path.join(dirpath, name)
                    rel = os.path.relpath(src_file, build_inc)
                    dst_file = os.path.join(self.package_folder, "include", rel)
                    if os.path.isfile(dst_file):
                        continue
                    os.makedirs(os.path.dirname(dst_file), exist_ok=True)
                    shutil.copyfile(src_file, dst_file)
                    staged_headers += 1
        if staged_headers < 300:
            raise ConanException(
                "xqilla manual install staged only {} headers "
                "(upstream include/ holds ~393); refusing to ship a "
                "partial header tree".format(staged_headers))
        # Library artefacts from the build tree (.libs preferred).
        lib_candidates = []
        for dirpath, _dirnames, filenames in os.walk(self.build_folder):
            for name in filenames:
                if name == "libxqilla.a" or name.startswith("libxqilla.so"):
                    lib_candidates.append(os.path.join(dirpath, name))
        if not lib_candidates:
            raise ConanException(
                "xqilla manual install found no libxqilla.a/.so under "
                "build_folder {}".format(self.build_folder))
        def _lib_rank(p):
            flat = p.replace(chr(92), "/")
            return (0 if ".libs" in flat else 1, len(p), p)
        staged_libs = set()
        for cand in sorted(lib_candidates, key=_lib_rank):
            base = os.path.basename(cand)
            if base in staged_libs:
                continue
            dst = os.path.join(self.package_folder, "lib", base)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(cand, dst)
            staged_libs.add(base)
            if base == "libxqilla.a":
                break
        if "libxqilla.a" not in staged_libs and not any(
                n.startswith("libxqilla.so") for n in staged_libs):
            raise ConanException(
                "xqilla manual install staged no library "
                "(candidates: {})".format(sorted(lib_candidates)))
        # CLI binary: libtool leaves a `xqilla` wrapper script plus the real
        # ELF at `.libs/xqilla`. Pick the largest non-script `xqilla` file.
        bin_candidates = []
        for dirpath, _dirnames, filenames in os.walk(self.build_folder):
            if "test_package" in dirpath.replace(chr(92), "/"):
                continue
            for name in filenames:
                if name != "xqilla":
                    continue
                full = os.path.join(dirpath, name)
                try:
                    if not os.path.isfile(full) or os.path.getsize(full) == 0:
                        continue
                    with open(full, "rb") as handle:
                        magic = handle.read(2)
                    if magic == b"#!":
                        continue  # libtool wrapper script, not the ELF
                except OSError:
                    continue
                bin_candidates.append(full)
        if not bin_candidates:
            raise ConanException(
                "xqilla manual install found no xqilla CLI binary under "
                "build_folder {}".format(self.build_folder))
        def _bin_rank(p):
            flat = p.replace(chr(92), "/")
            key_libs = 0 if ".libs" in flat else 1
            try:
                size = -os.path.getsize(p)
            except OSError:
                size = 0
            return (key_libs, size, p)
        best = sorted(bin_candidates, key=_bin_rank)[0]
        dst_bin = os.path.join(self.package_folder, "bin", "xqilla")
        os.makedirs(os.path.dirname(dst_bin), exist_ok=True)
        shutil.copyfile(best, dst_bin)
        self.output.info(
            "xqilla manual install: headers={} libs={} cli={}".format(
                staged_headers, sorted(staged_libs), best))

    def package(self):
        # HMBS sandbox masks install(1) (install-nobase_includeHEADERS
        # exits 64) and reports HMBS_CAP_CHMOD=0, so autotools.install()
        # cannot succeed here (xlslib precedent). Stage manually with
        # plain data copies mirroring `make install` exactly.
        self._manual_install()
        for pattern in ("*.la", "*.dylib"):
            rm(self, pattern,
               folder=os.path.join(self.package_folder, "lib"))
        binary = os.path.join(self.package_folder, "bin", "xqilla")
        if os.path.isfile(binary):
            try:
                os.chmod(binary, 0o755)
            except OSError:
                pass  # HMBS_CAP_CHMOD=0; exec bit from open mode / signing
            self._sign_elf(binary)

    def package_info(self):
        self.cpp_info.libs = ["xqilla"]
        self.cpp_info.set_property("cmake_file_name", "xqilla")
        self.cpp_info.set_property("cmake_target_name", "xqilla::xqilla")
        self.cpp_info.set_property("pkg_config_name", "xqilla")
        self.cpp_info.requires = ["xerces-c::xerces-c"]
        self.cpp_info.bindirs = ["bin"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs.extend(["m", "pthread"])
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
