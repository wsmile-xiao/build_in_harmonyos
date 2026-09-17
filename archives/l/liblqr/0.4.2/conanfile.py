#!/usr/bin/env python3
"""Conan recipe — liblqr 0.4.2 (Autotools).

Liquid Rescale seam-carving library (lqr-1). Autotools-only upstream
(configure + make), single runtime dependency on glib-2.0.
Upstream 0.4.2 ships no test suite (audited tarball, see
test_package/MANIFEST.yml): no tests/ dir, no TESTS/check_PROGRAMS,
so build() does not run make check; verification is via test_package.
"""
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import copy, get, rm
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class LiblqrConan(ConanFile):
    name = "liblqr"
    version = "0.4.2"
    description = (
        "The LiquidRescale (lqr) library provides a C/C++ API for performing "
        "non-uniform resizing of images by the seam-carving technique."
    )
    license = ("LGPL-3.0-or-later", "GPL-3.0-or-later")
    homepage = "http://liblqr.wikidot.com"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("image", "resizing", "seam-carving")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def requirements(self):
        # configure.ac: PKG_CHECK_MODULES(GLIB, glib-2.0 >= 2.8.0)
        # transitive_libs=True: static link needs glib's bundled libs
        # (intl/ffi via components) visible downstream (cassbeam precedent).
        # zlib override + exact pkgconf pin mirror merged ctpl/0.3.5 (same
        # glib/2.88.0 chain, CI-verified): keeps the dependency graph
        # identical to a proven-good one so prebuilt OHOS binaries hit.
        self.requires("zlib/1.3.1.1", override=True)
        self.requires("glib/2.88.0", transitive_headers=True,
                      transitive_libs=True)

    def build_requirements(self):
        # ctpl/0.3.5 precedent (merged): exact adapted pkgconf, not a
        # ConanCenter range that can resolve to an unadapted 2.x.
        self.tool_requires("pkgconf/3.0.5")

    def validate(self):
        # ctpl/0.3.5 precedent: only Linux and OHOS are supported.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "liblqr %s only supports Linux and OHOS, got os=%s"
                % (self.version, self.settings.os))

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # HMDFS fixes at source time, variable-expansion form only (no baked
        # absolute paths: source-time TMPDIR may differ from build-time).
        self._patch_configure_tree(self.source_folder)

    def generate(self):
        deps = AutotoolsDeps(self)
        deps.generate()
        pc = PkgConfigDeps(self)
        pc.generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--disable-install-man")
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        if str(self.settings.os) == "OHOS":
            # E007 functional fix (ctpl/cdecl/castget precedent): pin GNU
            # triplets so configure skips the config.guess probe entirely.
            # The 2009-era config.guess/config.sub predate OHOS by ~15
            # years and cannot recognise the ohos triplet; the previous
            # comment-append fallback was a no-op and is retired.
            tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
            tc.configure_args.append("--host=aarch64-unknown-linux-gnu")
        # E002/readonly_tmp + DRAFT-6487/classads: HMBS 注入的 TMPDIR 与 SHELL
        # 必须真正到达 configure 子进程。profile buildenv 会重导出
        # CONFIG_SHELL=/data/service/hnp/bin/bash（HMDFS 上 getcwd 失败，
        # 上轮已致 configure 重执行 "inaccessible or not found"）。除独立
        # hmbs_tmpdir 脚本外，再经 tc.environment() 写入工具链环境做双保险
        #（与 backuppc-rsync/3.1.3.0 同范式），值一律复用 HMBS 注入，
        # 不发明新路径。
        _tmp = (os.environ.get("TMPDIR") or os.environ.get("TMP")
                or os.environ.get("TEMP"))
        _shell_gen = os.environ.get("SHELL", "/bin/sh") or "/bin/sh"
        try:
            if _tmp:
                os.makedirs(_tmp, exist_ok=True)
        except Exception:
            pass
        _tc_env = tc.environment()
        if _tmp:
            _tc_env.define("TMPDIR", _tmp)
            _tc_env.define("TMP", _tmp)
            _tc_env.define("TEMP", _tmp)
        _tc_env.define("SHELL", _shell_gen)
        _tc_env.define("CONFIG_SHELL", _shell_gen)
        # pkgconf/3.0.5 ships bin/pkgconf WITHOUT a bin/pkg-config alias
        # (its package() raises on unexpected alias); liblqr 0.4.2's
        # 2009-era pkg.m4 probes `pkg-config` (PKG_CHECK_MODULES for glib).
        # Point $PKG_CONFIG at the tool binary (old macros honour the env
        # value); the `pkg-config` PATH shim itself is created in build()
        # (cassbeam/1.1 precedent).
        _pkgconf_tool = ""
        try:
            _bdep = self.dependencies.build.get("pkgconf")
            if _bdep is not None and _bdep.package_folder:
                _cand = os.path.join(str(_bdep.package_folder), "bin",
                                     "pkgconf")
                if os.path.isfile(_cand):
                    _pkgconf_tool = _cand
        except Exception:
            pass
        if _pkgconf_tool:
            _tc_env.define("PKG_CONFIG", _pkgconf_tool)
        tc.generate(env=_tc_env)
        _env = Environment()
        if _tmp:
            _env.define("TMPDIR", _tmp)
            _env.define("TMP", _tmp)
            _env.define("TEMP", _tmp)
        _env.define("SHELL", _shell_gen)
        _env.define("CONFIG_SHELL", _shell_gen)
        if _pkgconf_tool:
            _env.define("PKG_CONFIG", _pkgconf_tool)
        _env.vars(self).save_script("hmbs_tmpdir")

    def build(self):
        # pkg-config shim FIRST: configure hardcodes `pkg-config` but the
        # pkgconf tool package only ships `pkgconf` (no alias by design),
        # so `checking for pkg-config... no` -> PKG_CHECK_MODULES hard
        # error for glib (cassbeam/1.1 precedent). Shim dir goes first on
        # PATH (conanbuild.sh preserves $PATH tail) and $PKG_CONFIG points
        # at the shim so old and new pkg.m4 both resolve.
        shim_dir = self._ensure_pkg_config_shim()
        if shim_dir:
            try:
                os.environ["PATH"] = (shim_dir + os.pathsep
                                      + os.environ.get("PATH", ""))
                os.environ["PKG_CONFIG"] = os.path.join(shim_dir,
                                                        "pkg-config")
            except Exception:
                pass
        # HMDFS: getcwd() can fail inside Conan build dirs (broken parent
        # path chain); seed $PWD and chdir so the shell pwd builtin resolves
        # the cwd logically (same workaround as lzop/sipcalc/libclastfm).
        bf = self.build_folder
        if os.path.isdir(bf):
            os.chdir(bf)
            os.environ["PWD"] = bf
        # E002/readonly_tmp round 2: probe a truly writable tmp root (never
        # /tmp, which is a read-only erofs mount: preflight "can't create
        # temporary file /tmp/...: Read-only file system"). Only the
        # temp-file root is redirected; no tests are skipped or removed.
        _tmp = self._resolve_hmbs_tmp()
        try:
            os.makedirs(_tmp, exist_ok=True)
        except Exception:
            pass
        os.environ["TMPDIR"] = _tmp
        os.environ["TMP"] = _tmp
        os.environ["TEMP"] = _tmp
        fb = os.environ.get("HMBS_AUTOCONF_MKTEMP_FALLBACK")
        if fb and fb not in ("0", "1"):
            try:
                os.makedirs(fb, exist_ok=True)
            except OSError:
                os.environ["HMBS_AUTOCONF_MKTEMP_FALLBACK"] = _tmp
        # HMBS injects SHELL=/bin/sh; keep the injected value.
        # DRAFT-6487: os.environ alone loses to conanbuild.sh (profile
        # buildenv re-exports CONFIG_SHELL=/data/service/hnp/bin/bash when
        # the configure subprocess is spawned). Patch our own generated
        # scripts so the sourced value is already correct, then keep the
        # os.environ export as well for direct child processes.
        _shell = os.environ.get("SHELL", "/bin/sh") or "/bin/sh"
        os.environ["SHELL"] = _shell
        os.environ["CONFIG_SHELL"] = _shell
        self._fix_generated_shell_env(_shell, _tmp)
        # Re-apply variable-form patches at build time: source/export may
        # have refreshed file mtimes after source() in some Conan flows.
        self._patch_configure_tree(self.source_folder)
        # E236/E544 (zeitgeist/symmetrica/fplll precedent): ohpcd prebuilt
        # deps (glib chain -> pcre2) were built with prefix=/, so cache
        # .la carry libdir='//lib' and .pc carry prefix=/. libtool follows
        # dependency_libs '//lib/libpcre2-8.la' and dies with
        # "is not a valid libtool archive" (this round's exact error).
        # Fix cache metadata before configure (basename-routed, save+log).
        self._fix_ohpcd_dep_la_pc()
        # Compiler: prefer the toolchain value verbatim (ctpl/0.3.5 precedent,
        # same glib/2.88.0 chain). NEW evidence this round: the failure moved
        # past the shell re-exec (bash "inaccessible" line gone) yet
        # `checking for ...-gcc... /data/service/hnp/bin/clang` is still
        # followed by "C compiler cannot create executables". The same
        # /data/service/hnp/bin prefix already proved unrunnable for bash in
        # this sandbox, so the absolute CC may likewise fail to execute here.
        # _ensure_working_compiler() only replaces CC/CXX when the injected
        # absolute path is provably unrunnable (no --version rc=0) and a
        # PATH/conf-discovered candidate runs; otherwise it is a no-op and
        # configure's own checks decide (adapted dhex/0.69 + cstream/4.0.0).
        self._ensure_working_compiler()
        self.output.info(
            f"HMBS tmp root (probed writable): {_tmp} SHELL={_shell}")
        autotools = Autotools(self)
        try:
            autotools.configure()
        except Exception:
            # Never guess again from the one-line summary: print the real
            # compiler error for the next round's diagnosis.
            self._dump_config_log()
            raise
        # R9: single job — parallel make hits HMDFS jobserver fifo EPERM (E074)
        # Compiler temp files honour TMPDIR: exported above for make as well
        # so nothing falls back to readonly /tmp (readonly_tmp gate).
        # Post-configure safety net (zeitgeist precedent): configure bakes
        # GLIB_LIBS into Makefiles; any residual //lib/<name>.la is routed
        # to its owner package dir before make starts.
        self._fix_generated_la_refs()
        # E182/E188 (adms/aribb24/aircrack precedent): HMBS install shim
        # does not mkdir -p the DESTDIR lib dir, so libtool's
        # 'install -c .libs/*.a $pkg//lib/' leaves no file and the
        # follow-up 'chmod 644' dies with ENOENT (this round). Our own
        # cp/mkdir shim creates parent dirs and tolerates chmod=0.
        _shim = self._write_install_shim()
        self._redirect_install_to_shim(_shim)
        autotools.make(args=["-j1"])

    def package(self):
        # Redirect may have been written in build(); re-ensure here
        # because package() can run with a fresh env. Idempotent.
        try:
            _shim = self._write_install_shim()
            self._redirect_install_to_shim(_shim)
        except Exception as _e:
            self.output.warning("install shim setup failed: %s" % _e)
        autotools = Autotools(self)
        autotools.install()
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        copy(self, "COPYING*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "lqr-1")
        self.cpp_info.set_property("cmake_file_name", "liblqr")
        self.cpp_info.set_property("cmake_target_name", "liblqr::liblqr")
        # Headers install to include/lqr-1 (lqr/lqr.h + lqr/*.h)
        self.cpp_info.includedirs = [os.path.join("include", "lqr-1")]
        self.cpp_info.libs = ["lqr-1"]
        self.cpp_info.requires = ["glib::glib-2.0"]
        if self.settings.os in ("Linux", "FreeBSD", "OHOS"):
            self.cpp_info.system_libs.append("m")
        pc_dir = os.path.join(self.package_folder, "lib", "pkgconfig")
        self.buildenv_info.append_path("PKG_CONFIG_PATH", pc_dir)
        self.runenv_info.append_path("PKG_CONFIG_PATH", pc_dir)

    def _fix_generated_shell_env(self, shell, tmpdir):
        """DRAFT-6487: repair our own generator scripts before configure.

        Conan spawns `autotools.configure()` with an aggregated env built
        by sourcing conanbuild.sh + conanautotoolstoolchain.sh, which
        re-exports the profile buildenv value
        CONFIG_SHELL=/data/service/hnp/bin/bash AFTER our os.environ
        assignment. That HNP bash fails getcwd() on HMDFS build dirs, so
        configure's re-exec (`exec $CONFIG_SHELL ...`) dies with
        "inaccessible or not found" and every subsequent AC_TRY compile
        is misreported as "C compiler cannot create executables"
        (this round's exact log). Rewrite that single absolute path to
        the HMBS-injected shell (values only, no logic change) in our
        own build-folder scripts; never touches dependency caches or
        other libraries (PR atomicity kept).
        """
        _bad = "/data/service/hnp/bin/bash"
        if not shell or shell == _bad:
            shell = "/bin/sh"
        roots = []
        try:
            for cand in (self.build_folder, self.generators_folder):
                if cand and cand not in roots:
                    roots.append(cand)
        except Exception:
            roots = [self.build_folder]
        for root in roots:
            if not root or not os.path.isdir(root):
                continue
            for _dir, _, _files in os.walk(root):
                for _fn in _files:
                    if not _fn.endswith(".sh"):
                        continue
                    _p = os.path.join(_dir, _fn)
                    try:
                        with open(_p, "r", encoding="utf-8",
                                  errors="replace") as _f:
                            _content = _f.read()
                        if _bad not in _content:
                            continue
                        _content = _content.replace(_bad, shell)
                        with open(_p, "w", encoding="utf-8") as _f:
                            _f.write(_content)
                        self.output.info(
                            f"HMBS CONFIG_SHELL fix: {_p} -> {shell}")
                    except OSError:
                        pass

    def _ensure_pkg_config_shim(self):
        """Provide `pkg-config` on PATH via pkgconf (cassbeam/1.1 precedent).

        tool_requires pkgconf/3.0.5 alone is insufficient: its package
        explicitly ships bin/pkgconf WITHOUT a bin/pkg-config alias
        (package() raises on unexpected alias), so liblqr's 2009-era
        configure still reports `checking for pkg-config... no` and dies
        in PKG_CHECK_MODULES for glib. Create a hmbs-shims dir holding a
        pkg-config -> pkgconf symlink (symlink cap=1; copyfile fallback
        avoids HMDFS chmod=0) and return it for PATH prepend. Scoped to
        our own build_folder; never touches other libraries.
        """
        shim_dir = os.path.join(self.build_folder, "hmbs-shims")
        try:
            os.makedirs(shim_dir, exist_ok=True)
        except OSError:
            return ""
        pkgconf_bin = ""
        try:
            bdep = self.dependencies.build.get("pkgconf")
            if bdep is not None and bdep.package_folder:
                cand = os.path.join(str(bdep.package_folder), "bin",
                                    "pkgconf")
                if os.path.isfile(cand):
                    pkgconf_bin = cand
        except Exception:
            pass
        if not pkgconf_bin:
            for cand in (shutil.which("pkgconf") or "", "/usr/bin/pkgconf",
                         "/usr/local/bin/pkgconf"):
                try:
                    if cand and os.path.isfile(cand):
                        pkgconf_bin = cand
                        break
                except Exception:
                    continue
        if not pkgconf_bin:
            self.output.warning(
                "pkgconf binary not found; pkg-config shim skipped")
            return ""
        link = os.path.join(shim_dir, "pkg-config")
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
            self.output.info(f"pkg-config shim: {link} -> {pkgconf_bin}")
            return shim_dir
        except Exception as exc:
            self.output.warning(f"pkg-config shim failed: {exc}")
            return ""

    def _runnable(self, cmd):
        """True when `cmd --version` exits 0 (file exists + exec works)."""
        try:
            if not cmd:
                return False
            if os.path.sep in cmd or "/" in cmd:
                if not (os.path.isfile(cmd) and os.access(cmd, os.X_OK)):
                    return False
            r = subprocess.run([cmd, "--version"],
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL,
                               timeout=20, check=False)
            return r.returncode == 0
        except Exception:
            return False

    def _ensure_working_compiler(self):
        """Adapted dhex/0.69 + cstream/4.0.0: gated CC/CXX fallback.

        Only acts when the injected absolute CC/CXX is provably unrunnable
        in this environment (no `--version` rc=0). Discovery order: conf
        tools.build:compiler_executables value first, PATH lookup
        (clang/clang++, cc/c++, gcc/g++) second, baked absolute path last
        (and only if it runs). Rewrites CC/CXX assignments line-wise in our
        own build-folder generator scripts (*.sh) plus os.environ so the
        sourced conanbuild env and direct children agree. Healthy toolchain
        values are left untouched (no-op). Never touches dependency caches.
        """
        if str(self.settings.os) not in ("OHOS", "Linux"):
            return
        try:
            _conf = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        except Exception:
            _conf = {}
        _conf_c = _conf.get("c") if isinstance(_conf, dict) else None
        _conf_cxx = _conf.get("cpp") if isinstance(_conf, dict) else None

        def _pick(kind):
            cands = []
            if kind == "cc":
                if _conf_c:
                    cands.append(_conf_c)
                for _b in ("clang", "cc", "gcc"):
                    _w = shutil.which(_b)
                    if _w and _w not in cands:
                        cands.append(_w)
                    if _b not in cands:
                        cands.append(_b)
            else:
                if _conf_cxx:
                    cands.append(_conf_cxx)
                for _b in ("clang++", "c++", "g++"):
                    _w = shutil.which(_b)
                    if _w and _w not in cands:
                        cands.append(_w)
                    if _b not in cands:
                        cands.append(_b)
            for _c in cands:
                if self._runnable(_c):
                    return _c
            return None

        roots = []
        for cand in (self.build_folder, getattr(self, "generators_folder",
                                                None)):
            if cand and cand not in roots and os.path.isdir(cand):
                roots.append(cand)
        import re as _re
        _assign = _re.compile(r"^(\s*(?:export\s+)?(?:CC|CXX)=)(.*)$")
        for var, kind in (("CC", "cc"), ("CXX", "cxx")):
            cur = os.environ.get(var)
            if not cur:
                for root in roots:
                    for _dir, _, _files in os.walk(root):
                        for _fn in _files:
                            if not _fn.endswith(".sh"):
                                continue
                            try:
                                with open(os.path.join(_dir, _fn), "r",
                                          encoding="utf-8",
                                          errors="replace") as _f:
                                    for _line in _f:
                                        _s = _line.strip()
                                        _p = "export %s=" % var if _s.startswith("export ") else "%s=" % var
                                        if _s.startswith(_p):
                                            cur = _s[len(_p):].strip().strip("\"'")
                                            break
                                    if cur:
                                        break
                            except OSError:
                                continue
                        if cur:
                            break
                    if cur:
                        break
            if not cur:
                continue
            if self._runnable(cur):
                continue
            new = _pick(kind)
            if not new or new == cur:
                self.output.warning(
                    f"HMBS compiler check: {var}={cur} not runnable and no"
                    " working fallback found; leaving toolchain value")
                continue
            os.environ[var] = new
            fixed = 0
            for root in roots:
                for _dir, _, _files in os.walk(root):
                    for _fn in _files:
                        if not _fn.endswith(".sh"):
                            continue
                        _p = os.path.join(_dir, _fn)
                        try:
                            with open(_p, "r", encoding="utf-8",
                                      errors="replace") as _f:
                                _lines = _f.readlines()
                            _changed = False
                            for _i, _line in enumerate(_lines):
                                _m = _assign.match(_line.rstrip("\n"))
                                if not _m:
                                    continue
                                _head, _val = _m.group(1), _m.group(2).strip()
                                _q = "\"" if _val.startswith("\"") else ("'" if _val.startswith("'") else "")
                                _bare = _val.strip("\"'")
                                _names = _bare.split()
                                if not _names:
                                    continue
                                if _names[0] == cur:
                                    _names[0] = new
                                    _body = " ".join(_names)
                                    _lines[_i] = "%s%s%s%s\n" % (_head, _q, _body, _q) if _q else "%s%s\n" % (_head, _body)
                                    _changed = True
                            if _changed:
                                with open(_p, "w", encoding="utf-8") as _f:
                                    _f.writelines(_lines)
                                fixed += 1
                        except OSError:
                            continue
            self.output.info(
                f"HMBS compiler fallback: {var} {cur} -> {new}"
                f" ({fixed} script(s) rewritten)")

    def _write_install_shim(self):
        """E182/E188: cp/mkdir install shim (adms 2.3.7 precedent).

        The HMBS-provided install shim leaves the DESTDIR lib dir
        uncreated for libtool's 'install -c .libs/liblqr-1.a $pkg//lib/'
        (prefix=/ artefact), so the file never lands and libtool's
        follow-up 'chmod 644' fails with ENOENT (this round's exact
        error). This shim mkdir -p's the destination parent, copies
        every source (single- and multi-source forms), and tolerates
        chmod=0 with '|| true'. Created with os.open(mode 0o755) so no
        separate chmod is needed on HMDFS (chmod cap=0); the trailing
        os.chmod is best-effort only.
        """
        shim_dir = os.path.join(self.build_folder, "_ohos_install_shim")
        try:
            os.makedirs(shim_dir, exist_ok=True)
        except OSError:
            pass
        install = os.path.join(shim_dir, "install")
        fd = os.open(install, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o755)
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
                "mkdir -p \"$(dirname \"$dest\")\"\n"
                "i=1\n"
                "for src in \"$@\"; do\n"
                "  [ $i -gt $count ] && break\n"
                "  cp -f \"$src\" \"$dest\"\n"
                "  if [ -n \"$mode\" ]; then\n"
                "    if [ -d \"$dest\" ]; then\n"
                "      chmod \"$mode\" \"$dest/${src##*/}\" 2>/dev/null || true\n"
                "    else\n"
                "      chmod \"$mode\" \"$dest\" 2>/dev/null || true\n"
                "    fi\n"
                "  fi\n"
                "  i=$((i + 1))\n"
                "done\n"
            )
        try:
            os.chmod(install, 0o755)
        except OSError:
            pass
        return install

    def _redirect_install_to_shim(self, shim_install):
        """Point generated Makefiles' INSTALL at our shim (adms precedent).

        configure bakes the probed install path into every Makefile's
        'INSTALL = .../install ...' line; INSTALL_DATA/INSTALL_PROGRAM
        reference ${INSTALL} so they follow automatically. Only our own
        build-tree Makefiles are rewritten; dependency caches untouched.
        """
        bf = self.build_folder
        if not bf or not os.path.isdir(bf):
            return
        for root, _, files in os.walk(bf):
            for name in files:
                if name != "Makefile":
                    continue
                mp = os.path.join(root, name)
                try:
                    with open(mp, "r", encoding="utf-8",
                              errors="ignore") as f:
                        content = f.read()
                except OSError:
                    continue
                if "INSTALL =" not in content:
                    continue
                lines = []
                changed = False
                for line in content.splitlines(True):
                    stripped = line.lstrip()
                    if stripped.startswith("INSTALL = ") and (
                            "/install" in stripped or "install" in stripped):
                        indent = line[:len(line) - len(stripped)]
                        lines.append("%sINSTALL = %s\n" % (indent,
                                                           shim_install))
                        changed = True
                    else:
                        lines.append(line)
                if changed:
                    try:
                        with open(mp, "w", encoding="utf-8") as f:
                            f.write("".join(lines))
                        self.output.info("INSTALL redirected: %s" % mp)
                    except OSError:
                        pass

    def _fix_ohpcd_dep_la_pc(self):
        """E236/E544: repair ohpcd prefix=/ dependency metadata.

        ohpcd binary deps are built with --prefix=/, so their installed
        .la files carry libdir='//lib' (or '/lib') plus dependency_libs
        entries such as '//lib/libpcre2-8.la', and their .pc files carry
        a bare 'prefix=/' line (libdir then expands to //lib). libtool
        resolves dependency_libs by absolute path, so the liblqr link
        fails with "sed: can't read //lib/libpcre2-8.la" /
        "'//lib/libpcre2-8.la' is not a valid libtool archive"
        (this round's exact log; same family as zeitgeist, symmetrica,
        fplll, E544/openconnect).

        Pass 1 collects basename->owner-libdir for every dependency .la
        (E544 trap: //lib/<name>.la must route to the package that owns
        <name>, not to the .la currently being edited). Pass 2 rewrites
        libdir, //lib/<name>.la references and -L//lib/-L/lib flags, then
        saves + logs (E544 trap: compute new -> save -> log, all three).
        .pc files only get the exact 'prefix=/' line replaced with the
        real package_folder (zeitgeist precedent: avoid substring damage
        to already-correct '/storage/...' prefixes); hardcoded
        libdir/include lines pointing at //lib/ /lib are pointed at the
        real lib/include dirs.
        """
        try:
            deps = list(self.dependencies.values())
        except Exception:
            return
        owner = {}
        la_files = []
        for dep in deps:
            try:
                pf = getattr(dep, "package_folder", None)
            except Exception:
                continue
            if not pf:
                continue
            lib_dir = os.path.join(str(pf), "lib")
            if not os.path.isdir(lib_dir):
                continue
            try:
                names = os.listdir(lib_dir)
            except OSError:
                continue
            for n in names:
                if n.endswith(".la"):
                    owner[n] = lib_dir
                    la_files.append(os.path.join(lib_dir, n))
        import re as _re
        la_ref = _re.compile(r"//lib/([A-Za-z0-9_+\-.]+\.la)")
        for p in la_files:
            try:
                with open(p, "r", encoding="utf-8", errors="replace") as f:
                    c = f.read()
            except OSError:
                continue
            orig = c

            def _route(m):
                base = m.group(1)
                dest = owner.get(base)
                if dest:
                    return dest + "/" + base
                cur_dir = os.path.dirname(p)
                return cur_dir + "/" + base

            c = la_ref.sub(_route, c)
            cur_dir = os.path.dirname(p)
            c = c.replace("libdir='//lib'", "libdir='%s'" % cur_dir)
            c = c.replace('libdir="//lib"', 'libdir="%s"' % cur_dir)
            c = c.replace("libdir='/lib'", "libdir='%s'" % cur_dir)
            c = c.replace('libdir="/lib"', 'libdir="%s"' % cur_dir)
            c = c.replace("-L//lib", "-L%s" % cur_dir)
            # Lone system -L/lib (prefix=/ artefact); the OHOS root
            # /lib never holds conan archives, so routing it to the real
            # dep lib dir is safe and keeps -l resolution working.
            c = c.replace("-L/lib", "-L%s" % cur_dir)
            if c != orig:
                try:
                    with open(p, "w", encoding="utf-8") as f:
                        f.write(c)
                    self.output.info("fixed .la paths: %s" % p)
                except OSError as e:
                    self.output.warning("cannot save %s: %s" % (p, e))
        for dep in deps:
            try:
                pf = getattr(dep, "package_folder", None)
            except Exception:
                continue
            if not pf:
                continue
            pf_s = str(pf)
            pc_dir = os.path.join(pf_s, "lib", "pkgconfig")
            if not os.path.isdir(pc_dir):
                continue
            try:
                names = os.listdir(pc_dir)
            except OSError:
                continue
            for n in names:
                if not n.endswith(".pc"):
                    continue
                pp = os.path.join(pc_dir, n)
                try:
                    with open(pp, "r", encoding="utf-8",
                              errors="replace") as f:
                        lines = f.read().split("\n")
                except OSError:
                    continue
                changed = False
                out = []
                for ln in lines:
                    if ln.strip() == "prefix=/":
                        out.append("prefix=%s" % pf_s)
                        changed = True
                    elif ln.startswith("libdir=") and ln.split(
                            "=", 1)[1].strip() in ("//lib", "/lib",
                                                   "${prefix}/lib"):
                        # Only rewrite when the resolved prefix was the
                        # broken '/' one; generated correct files keep
                        # absolute storage paths untouched.
                        out.append("libdir=%s"
                                   % os.path.join(pf_s, "lib"))
                        changed = True
                    elif ln.startswith("includedir=") and ln.split(
                            "=", 1)[1].strip() in ("//include",
                                                   "/include",
                                                   "${prefix}/include"):
                        out.append("includedir=%s"
                                   % os.path.join(pf_s, "include"))
                        changed = True
                    else:
                        out.append(ln)
                if changed:
                    try:
                        with open(pp, "w", encoding="utf-8") as f:
                            f.write("\n".join(out))
                        self.output.info("fixed pc %s" % n)
                    except OSError as e:
                        self.output.warning("cannot save %s: %s" % (pp, e))

    def _fix_generated_la_refs(self):
        """Post-configure net: reroute residual //lib refs in Makefiles.

        GLIB_LIBS is baked into Makefiles at configure time, so a stale
        '//lib/libpcre2-8.la' can survive even after the cache fix if
        configure ran before it. Scan our own build tree (never dep
        caches) and reroute '//lib/<name>.la' by basename to its owner
        lib dir; bare '-L//lib'/'-I//include' fall back to the pcre2
        owner (the only //lib producer in this glib chain). Only
        basename-known .la references are rewritten, so our own
        liblqr libdir line is untouched.
        """
        try:
            deps = list(self.dependencies.values())
        except Exception:
            deps = []
        owner = {}
        for dep in deps:
            try:
                pf = getattr(dep, "package_folder", None)
            except Exception:
                continue
            if not pf:
                continue
            lib_dir = os.path.join(str(pf), "lib")
            if not os.path.isdir(lib_dir):
                continue
            try:
                for n in os.listdir(lib_dir):
                    if n.endswith(".la") and n not in owner:
                        owner[n] = lib_dir
            except OSError:
                continue
        if not owner:
            return
        import re as _re
        la_ref = _re.compile(r"//lib/([A-Za-z0-9_+\-.]+\.la)")
        fallback_lib = ""
        fallback_inc = ""
        try:
            for dep in deps:
                r = str(getattr(getattr(dep, "ref", None), "name", "")
                        or getattr(dep, "ref", ""))
                if "pcre2" in r:
                    pf = str(dep.package_folder)
                    fallback_lib = os.path.join(pf, "lib")
                    fallback_inc = os.path.join(pf, "include")
                    break
        except Exception:
            pass
        if not fallback_lib:
            fallback_lib = next(iter(owner.values()))
        roots = []
        for cand in (self.build_folder, self.source_folder):
            if cand and os.path.isdir(cand) and cand not in roots:
                roots.append(cand)
        for root in roots:
            for _dir, _, _files in os.walk(root):
                for _fn in _files:
                    if not (_fn == "Makefile" or _fn.startswith("Makefile")
                            or _fn.endswith(".la") or _fn.endswith(".pc")):
                        continue
                    _p = os.path.join(_dir, _fn)
                    try:
                        with open(_p, "r", encoding="utf-8",
                                  errors="replace") as _f:
                            _c = _f.read()
                    except OSError:
                        continue
                    _orig = _c

                    def _route(m):
                        base = m.group(1)
                        dest = owner.get(base)
                        if dest:
                            return dest + "/" + base
                        return m.group(0)

                    _c = la_ref.sub(_route, _c)
                    if fallback_lib and "-L//lib" in _c:
                        _c = _c.replace("-L//lib", "-L%s" % fallback_lib)
                    if fallback_lib and " -L/lib " in _c:
                        _c = _c.replace(" -L/lib ",
                                        " -L%s " % fallback_lib)
                    if fallback_inc and "-I//include" in _c:
                        _c = _c.replace("-I//include",
                                        "-I%s" % fallback_inc)
                    if _c != _orig:
                        try:
                            with open(_p, "w", encoding="utf-8") as _f:
                                _f.write(_c)
                            self.output.info(
                                "fixed //lib in %s"
                                % os.path.relpath(_p, root))
                        except OSError:
                            pass

    def _dump_config_log(self):
        """Print config.log tail so the next round sees the real error."""
        cands = []
        for base in (self.build_folder, self.source_folder):
            if not base or not os.path.isdir(base):
                continue
            for _dir, _, _files in os.walk(base):
                if "config.log" in _files:
                    cands.append(os.path.join(_dir, "config.log"))
        for _p in cands[:2]:
            try:
                with open(_p, "r", encoding="utf-8", errors="replace") as _f:
                    _lines = _f.read().splitlines()
                self.output.error(f"===== config.log tail: {_p} =====")
                for _line in _lines[-60:]:
                    self.output.error(f"config.log| {_line}"[:2000])
                self.output.error("===== end config.log tail =====")
            except OSError as _e:
                self.output.warning(f"cannot read {_p}: {_e}")
        if not cands:
            self.output.warning("no config.log found under build/source")

    def _resolve_hmbs_tmp(self):
        """Pick a writable tmp dir: probe candidates, never /tmp (readonly erofs)."""
        def _valid(p):
            try:
                if not p or p in ("0", "1") or p == "/tmp":
                    return False
                os.makedirs(p, exist_ok=True)
                probe = os.path.join(p, ".hmbs_probe")
                with open(probe, "w") as _pf:
                    _pf.write("probe")
                os.remove(probe)
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
        fb = os.path.join(self.build_folder, "cfg-tmp")
        try:
            os.makedirs(fb, exist_ok=True)
        except OSError:
            pass
        return fb

    def _patch_configure(self, cfg):
        """Variable-form tmp redirection for one configure script.

        mktemp templates -> ${TMPDIR:-.} and autoconf's ${TMPDIR=/tmp}
        default -> ${TMPDIR=.} so temp dirs never land on readonly /tmp.
        No absolute paths are baked: the variable is resolved at build
        time from the exported environment.
        """
        try:
            with open(cfg, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            orig = content
            if "umask 077" in content:
                content = content.replace("umask 077", "umask 022")
            # getcwd may fail on HMDFS: fall back to $PWD.
            if "ac_pwd=`pwd`" in content:
                content = content.replace(
                    "ac_pwd=`pwd`",
                    'ac_pwd=`pwd` 2>/dev/null || ac_pwd="$PWD"')
            # mktemp templates -> $TMPDIR (variable form, no baked paths).
            content = content.replace(
                'mktemp -d -q "./confstatXXXXXX"',
                'mktemp -d -q "${TMPDIR:-.}/confstatXXXXXX"')
            content = content.replace(
                'mktemp -d "./confXXXXXX"',
                'mktemp -d "${TMPDIR:-.}/confXXXXXX"')
            content = content.replace(
                "mktemp -d './confXXXXXX'",
                "mktemp -d '${TMPDIR:-.}/confXXXXXX'")
            # Older autoconf fallbacks: tmp=./conf$ variants -> $TMPDIR.
            content = content.replace(
                "tmp=./conf$-$RANDOM", "tmp=${TMPDIR:-.}/conf$-$RANDOM")
            if "tmp=./conf$" in content and "${TMPDIR" not in content.split("tmp=./conf$")[0][-200:]:
                content = content.replace("tmp=./conf", "tmp=${TMPDIR:-.}/conf")
            # Do not let autoconf default TMPDIR to readonly /tmp.
            content = re.sub(r":\s*\$\{TMPDIR=/tmp\}", ": ${TMPDIR=\\.}", content)
            content = content.replace("${TMPDIR=/tmp}", "${TMPDIR=\\.}")
            if content != orig:
                with open(cfg, "w", encoding="utf-8") as f:
                    f.write(content)
                self.output.info(f"HMDFS tmp patch applied: {cfg}")
        except OSError:
            pass

    def _patch_configure_tree(self, root):
        for _root, _, files in os.walk(root):
            if "configure" in files:
                self._patch_configure(os.path.join(_root, "configure"))
