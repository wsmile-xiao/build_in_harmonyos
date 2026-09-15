#!/usr/bin/env python3
"""Conan recipe -- dcap 2.47.14 (autotools, GitHub archive has no configure).

dCache access protocol client library: libdcap, libpdcap (LD_PRELOAD),
dccp client tool and IO tunnel plugins.

OHOS notes:
1. Upstream GitHub tag tarball has no configure; generate it following
   bootstrap.sh (mkdir -p config / aclocal -I config / autoheader /
   libtoolize --automake / automake --add-missing --copy --foreign /
   autoconf). tool_requires: automake/1.18, autoconf/2.72, libtool/2.5.4.
   Do not use autoreconf -fi: the conan automake wrapper references
   bin/.*-real which may be missing on HMDFS (exit 126); call
   $pkg/bin/.*-real directly with the system perl and explicit
   --automake-acdir/--system-acdir/--libdir args, falling back to system
   tools when the real files are absent. Force PERL to the system perl.
2. config.guess does not know HarmonyOS; pass explicit --build/--host so
   the upstream main linux-gnu branch is taken.
3. The generated configure creates conf temp dirs with umask 077 which
   fails on HMDFS; replace with umask 022 before running.
4. Parallel make trips HMDFS jobserver fifo EPERM; always build with -j1.
5. zlib is a hard upstream requirement (configure errors out without it);
   openssl enables the ssl tunnel plugin. CUnit is test-only via
   test_requires and provides the upstream make check suite.
6. musl/OHOS has an opaque FILE type, so src/dcap_stream.c (which pokes
   glibc FILE internals and fabricates FILE * via malloc(sizeof(FILE)))
   is patched (see conandata patches): private heap tokens + registry
   on Linux without __GLIBC__, untouched elsewhere.
7. HarmonyOS preflight mounts /tmp read-only: every /bin/sh -c wrapper
   fails with "can't create temporary file /tmp/shXXXX.tmp". All recipe
   subprocesses therefore run via list-form subprocess (no shell) with a
   writable TMPDIR/TMP/TEMP forwarded in source/generate/build/package.
8. Install directly into the Conan package folder (zzuf precedent):
   configure gets an explicit --prefix=<package_folder> (the manual
   list-form configure bypasses Autotools.configure(), which is what
   normally appends it) and package() runs plain `make install` with an
   empty DESTDIR.
9. Device `make install` exits 0 yet lands only libLTLIBRARIES (preflight
   evidence: package tree held just lib/*.so, no include/bin/share), so
   package() takes explicit ownership of the documented layout with Conan
   copy(): h_sources -> <package_folder>/include (mirrors
   library_include_HEADERS) and the built dccp -> <package_folder>/bin
   (mirrors install-binPROGRAMS), then asserts the public headers.

Upstream tests: tests/test_url.c, 11 CUnit cases (offline URL parsing),
run at the end of build() via make check with test-suite.log parsing.
"""
import json
import os
import re
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class DcapConan(ConanFile):
    name = "dcap"
    version = "2.47.14"
    description = "dCache access protocol client library"
    license = "LGPL-2.1-only"
    homepage = "https://www.dcache.org"
    url = "https://github.com/dCache/dcap"

    package_type = "library"
    required_conan_version = ">=2.0"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1")
        self.requires("openssl/3.5.6")

    def build_requirements(self):
        self.tool_requires("automake/1.18")
        self.tool_requires("autoconf/2.72")
        self.tool_requires("libtool/2.5.4")
        self.test_requires("cunit/2.1-3")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "dcap is only supported on Linux/OHOS, not {}".format(self.settings.os)
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        self._ensure_tmp_env()
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        self._ensure_tmp_env()
        VirtualBuildEnv(self).generate()
        tc = AutotoolsToolchain(self)
        for _dep_name in ("zlib", "openssl", "cunit"):
            if _dep_name not in self.dependencies:
                continue
            _dep = self.dependencies[_dep_name]
            _root = str(_dep.package_folder)
            for _inc in _dep.cpp_info.includedirs:
                _p = _inc if os.path.isabs(_inc) else os.path.join(_root, _inc)
                tc.extra_cflags.append("-I" + _p)
            for _lib in _dep.cpp_info.libdirs:
                _p = _lib if os.path.isabs(_lib) else os.path.join(_root, _lib)
                tc.extra_ldflags.append("-L" + _p)
        # Install directly into the Conan package folder (zzuf precedent):
        # plain `make install` with no DESTDIR. Explicit prefix here keeps
        # the generated toolchain script consistent with the manual
        # list-form configure invocation in build().
        try:
            tc.prefix = self.package_folder
        except Exception:
            pass
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.configure_args.append("--host=aarch64-unknown-linux-gnu")
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--disable-shared", "--enable-static"])
            if self.options.get_safe("fPIC"):
                tc.extra_cflags.append("-fPIC")
        tc.generate()
        _tmp = self._writable_tmpdir()
        _hmbs_env = Environment()
        _hmbs_env.define("TMPDIR", _tmp)
        _hmbs_env.define("TMP", _tmp)
        _hmbs_env.define("TEMP", _tmp)
        _hmbs_env.define("SHELL", "/bin/sh")
        _hmbs_env.define("CONFIG_SHELL", "/bin/sh")
        for _k in ("HMBS_AUTOCONF_MKTEMP_FALLBACK", "HMBS_CAP_LOCAL_MKTEMP",
                   "HMBS_CAP_HARDLINK", "HMBS_CAP_CHMOD", "HMBS_CAP_SYMLINK",
                   "HMBS_TMPDIR", "HMBS_CMAKE", "HMBS_MAKE", "HMBS_NINJA",
                   "HMBS_PYTHON3"):
            _v = os.environ.get(_k)
            if _v:
                _hmbs_env.define(_k, _v)
        _hmbs_env.vars(self, scope="build").save_script("hmbs_env")

    def _writable_tmpdir(self):
        # Priority: HMBS runtime tmp > platform-capabilities tmpdir >
        # already-exported TMPDIR/TMP/TEMP (unless bare /tmp which is
        # read-only erofs on the real device) > autoconf fallback >
        # per-folder tmp under build/source folders.
        _cands = []
        for _k in ("HMBS_TMPDIR", "HMBS_TMPDIR_RUNTIME"):
            _v = os.environ.get(_k)
            if _v:
                _cands.append(_v)
        _pc = os.environ.get("HMBS_PLATFORM_CAPABILITIES")
        if _pc:
            try:
                _obj = json.loads(_pc)
                if isinstance(_obj, dict):
                    for _k in ("tmpdir", "tmpDir", "TMPDIR"):
                        if _obj.get(_k):
                            _cands.append(str(_obj[_k]))
            except Exception:
                pass
        for _k in ("TMPDIR", "TMP", "TEMP"):
            _v = os.environ.get(_k)
            if _v and _v != "/tmp" and _v not in _cands:
                _cands.append(_v)
        _fb = os.environ.get("HMBS_AUTOCONF_MKTEMP_FALLBACK")
        if _fb:
            _cands.append(_fb)
        for _base in (getattr(self, "build_folder", None),
                      getattr(self, "base_build_folder", None),
                      getattr(self, "source_folder", None),
                      getattr(self, "base_source_folder", None)):
            if _base:
                _cands.append(os.path.join(str(_base), "tmp"))
        for _c in _cands:
            if not _c:
                continue
            try:
                os.makedirs(_c, exist_ok=True)
            except OSError:
                continue
            if not os.path.isdir(_c):
                continue
            try:
                _probe = os.path.join(_c, ".hmbs_wtest")
                with open(_probe, "w", encoding="utf-8") as _f:
                    _f.write("w")
                os.remove(_probe)
                return _c
            except OSError:
                continue
        # Last resort: build_folder/tmp even if the probe above failed;
        # caller still exports it so mktemp has a non-/tmp root.
        try:
            _d = os.path.join(str(self.build_folder), "tmp")
            os.makedirs(_d, exist_ok=True)
            return _d
        except Exception:
            return "/tmp"

    def _ensure_tmp_env(self):
        _tmp = self._writable_tmpdir()
        try:
            os.makedirs(_tmp, exist_ok=True)
        except OSError:
            pass
        for _k in ("TMPDIR", "TMP", "TEMP"):
            os.environ[_k] = _tmp
        os.environ["SHELL"] = "/bin/sh"
        os.environ["CONFIG_SHELL"] = "/bin/sh"
        try:
            os.umask(0o022)
        except Exception:
            pass
        return _tmp

    def _conan_script_env(self, env):
        # Re-apply what `self.run(..., env="conanbuild")` would source
        # (conanbuild.sh + toolchain scripts) so list-form subprocess
        # keeps CC/CFLAGS/LDFLAGS/PATH without going through /bin/sh -c.
        _dirs = []
        for _attr in ("generators_folder", "build_folder",
                      "base_build_folder"):
            try:
                _d = getattr(self, _attr, None)
            except Exception:
                _d = None
            if _d and os.path.isdir(str(_d)) and str(_d) not in _dirs:
                _dirs.append(str(_d))
        for _d in _dirs:
            for _fn in ("conanbuild.sh", "conanautotoolstoolchain.sh",
                        "conanautotoolsdeps.sh"):
                _p = os.path.join(_d, _fn)
                if not os.path.isfile(_p):
                    continue
                try:
                    with open(_p, "r", encoding="utf-8",
                              errors="replace") as _f:
                        for _line in _f.read().splitlines():
                            _line = _line.strip()
                            if not _line or _line.startswith("#"):
                                continue
                            _m = re.match(
                                r"^(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)=(.*)$",
                                _line)
                            if not _m:
                                continue
                            _k, _v = _m.group(1), _m.group(2).strip()
                            if len(_v) >= 2 and ((_v[0] == '"' and _v[-1] == '"')
                                                or (_v[0] == "'" and _v[-1] == "'")):
                                _v = _v[1:-1]
                            def _sub(_mt):
                                _name = _mt.group(1) or _mt.group(2)
                                return env.get(_name, os.environ.get(_name, ""))
                            _v = re.sub(r"\$\{([^}]+)\}|\$([A-Za-z_][A-Za-z0-9_]*)",
                                        _sub, _v)
                            if _k in ("TMPDIR", "TMP", "TEMP", "SHELL",
                                      "CONFIG_SHELL"):
                                continue
                            env[_k] = _v
                except OSError:
                    continue
        return env

    def _run(self, argv, cwd=None, extra_env=None):
        # List-form direct exec, never `sh -c`: avoids the read-only
        # /tmp/shXXXX.tmp failure of /bin/sh startup on the device.
        if isinstance(argv, str):
            raise ConanException(
                "dcap _run requires a list argv (no shell): {!r}".format(argv))
        _tmp = self._ensure_tmp_env()
        _env = dict(os.environ)
        _env["TMPDIR"] = _tmp
        _env["TMP"] = _tmp
        _env["TEMP"] = _tmp
        _env["SHELL"] = "/bin/sh"
        _env["CONFIG_SHELL"] = "/bin/sh"
        self._conan_script_env(_env)
        # Make sure conan tool_requires + HMBS tool dirs are on PATH even
        # when the generated scripts are not yet on disk (bootstrap phase).
        _path_dirs = []
        try:
            _build_deps = self.dependencies.build
            for _name in ("automake", "autoconf", "libtool", "m4", "perl"):
                try:
                    if _name in _build_deps:
                        _b = os.path.join(
                            str(_build_deps[_name].package_folder), "bin")
                        if os.path.isdir(_b):
                            _path_dirs.append(_b)
                except Exception:
                    continue
        except Exception:
            pass
        for _k in ("HMBS_CMAKE", "HMBS_MAKE", "HMBS_NINJA", "HMBS_PYTHON3"):
            _v = os.environ.get(_k) or _env.get(_k)
            if _v:
                _dd = os.path.dirname(str(_v))
                if os.path.isdir(_dd):
                    _path_dirs.append(_dd)
        for _d in ("/data/service/hnp/bin", "/usr/local/bin",
                   "/usr/bin", "/bin"):
            if os.path.isdir(_d):
                _path_dirs.append(_d)
        if _path_dirs:
            _cur = _env.get("PATH", os.environ.get("PATH", ""))
            _parts = [p for p in _cur.split(os.pathsep) if p] if _cur else []
            for _d in _path_dirs:
                if _d not in _parts:
                    _parts.insert(0, _d)
            # Deduplicate while keeping order.
            _seen = set()
            _uniq = []
            for _p in _parts:
                if _p not in _seen:
                    _seen.add(_p)
                    _uniq.append(_p)
            _env["PATH"] = os.pathsep.join(_uniq)
        if extra_env:
            for _k, _v in extra_env.items():
                _env[str(_k)] = str(_v)
        # Re-assert writable tmp after script sourcing.
        _env["TMPDIR"] = _tmp
        _env["TMP"] = _tmp
        _env["TEMP"] = _tmp
        self.output.info("dcap exec: " + " ".join(argv))
        try:
            _rc = subprocess.run(argv, cwd=cwd, env=_env,
                                 shell=False).returncode
        except OSError as _exc:
            raise ConanException(
                "dcap exec failed {}: {!r}".format(argv, _exc))
        if _rc != 0:
            raise ConanException(
                "dcap exec failed (rc={}): {}".format(_rc, " ".join(argv)))

    def _resolve_cc(self):
        _conf_cc = None
        try:
            _conf_cc = self.conf.get("tools.build:compiler_executables:c", check_type=str)
        except Exception:
            _conf_cc = None
        if _conf_cc and os.path.isfile(_conf_cc) and os.access(_conf_cc, os.X_OK):
            return _conf_cc
        for _name in ("clang", "cc", "gcc"):
            _w = shutil.which(_name)
            if _w and os.path.isfile(_w):
                return _w
        return _conf_cc or "clang"

    def _resolve_make(self):
        for _k in ("HMBS_MAKE",):
            _v = os.environ.get(_k)
            if _v and os.path.isfile(_v):
                return _v
        _w = self._which(["make", "gmake"])
        if _w:
            return _w
        _s = self._system_tool(["make", "gmake"])
        return _s if _s else "make"

    def _which(self, names):
        for _n in names:
            for _d in os.environ.get("PATH", "").split(os.pathsep):
                if not _d:
                    continue
                _p = os.path.join(_d, _n)
                if os.path.isfile(_p):
                    return _p
        return None

    def _system_tool(self, names):
        _cands = []
        for _d in os.environ.get("PATH", "").split(os.pathsep):
            if not _d or "conan-home" in _d:
                continue
            for _n in names:
                _p = os.path.join(_d, _n)
                if os.path.isfile(_p):
                    _cands.append(_p)
        for _d in ("/data/service/hnp/bin", "/usr/local/bin",
                   "/usr/bin", "/bin"):
            for _n in names:
                _p = os.path.join(_d, _n)
                if os.path.isfile(_p) and _p not in _cands:
                    _cands.append(_p)
        return _cands[0] if _cands else None

    def _perl(self):
        for _p in ("/data/service/hnp/bin/perl",):
            if os.path.isfile(_p) and os.access(_p, os.X_OK):
                return _p
        for _d in os.environ.get("PATH", "").split(os.pathsep):
            if not _d or "conan-home" in _d:
                continue
            _p = os.path.join(_d, "perl")
            if os.path.isfile(_p):
                return _p
        _w = shutil.which("perl")
        return _w if _w else "perl"

    def _bootstrap(self):
        self._ensure_tmp_env()
        _perl = self._perl()
        _build = self.dependencies.build
        _automake_root = str(_build["automake"].package_folder) \
            if "automake" in _build else ""
        _autoconf_root = str(_build["autoconf"].package_folder) \
            if "autoconf" in _build else ""
        self.output.info("dcap bootstrap: perl={} automake_root={} "
                         "autoconf_root={}".format(
                             _perl, _automake_root, _autoconf_root))

        def _real(_root, _names):
            for _n in _names:
                _p = os.path.join(_root, "bin", _n) if _root else ""
                if _p and os.path.isfile(_p):
                    return _p
            return None

        _aclocal_real = _real(_automake_root, [".aclocal-real", "aclocal-real"])
        _automake_real = _real(_automake_root,
                               [".automake-real", "automake-real"])
        _autoconf_real = _real(_autoconf_root,
                               [".autoconf-real", "autoconf-real"])
        _autoheader_real = _real(_autoconf_root,
                                 [".autoheader-real", "autoheader-real"])
        _libtool_root = str(_build["libtool"].package_folder) \
            if "libtool" in _build else ""
        if not _libtool_root and "libtool" in self.dependencies:
            try:
                _libtool_root = str(
                    self.dependencies["libtool"].package_folder)
            except Exception:
                _libtool_root = ""
        # aclocal must see libtool.m4/ltoptions.m4/... otherwise the
        # generated aclocal.m4 lacks LT_INIT and every Libtool library
        # target fails with "'LIBTOOL' is undefined".
        _extra_acdirs = []
        for _cand in (
                os.path.join(_libtool_root, "share", "aclocal")
                if _libtool_root else "",
                os.path.join(_libtool_root, "res", "aclocal")
                if _libtool_root else "",
                os.path.join(_automake_root, "share", "aclocal")
                if _automake_root else ""):
            if _cand and os.path.isdir(_cand) \
                    and _cand not in _extra_acdirs:
                _extra_acdirs.append(_cand)
        _aclocal_path = os.pathsep.join(_extra_acdirs)
        self.output.info(
            "dcap bootstrap: libtool_root={} extra_acdirs={}".format(
                _libtool_root, _extra_acdirs))
        self.output.info(
            "dcap bootstrap: real files aclocal={} automake={} "
            "autoconf={} autoheader={}".format(
                _aclocal_real, _automake_real,
                _autoconf_real, _autoheader_real))

        try:
            os.makedirs(os.path.join(self.source_folder, "config"),
                        exist_ok=True)
        except OSError:
            pass
        _install_sh = os.path.join(self.source_folder, "config",
                                   "install-sh")
        if not os.path.isfile(_install_sh):
            try:
                with open(_install_sh, "w", encoding="utf-8",
                          newline="\n") as _f:
                    _f.write("#!/bin/sh\n# placeholder for libtoolize "
                             "aux-dir heuristic\n")
            except OSError:
                pass
        _libtoolize = self._which(["libtoolize", "glibtoolize"])
        if _libtoolize:
            self._run([_libtoolize, "--automake", "--copy", "--force"],
                      cwd=self.source_folder,
                      extra_env={"PERL": _perl})
        for _dst in (os.path.join(self.source_folder, "ltmain.sh"),
                     os.path.join(self.source_folder, "config",
                                  "ltmain.sh")):
            if os.path.isfile(_dst):
                continue
            _src = None
            try:
                _lt_pkg = None
                if "libtool" in _build:
                    _lt_pkg = str(_build["libtool"].package_folder)
                elif "libtool" in self.dependencies:
                    _lt_pkg = str(
                        self.dependencies["libtool"].package_folder)
                for _cand in (
                        os.path.join(_lt_pkg or "", "share", "libtool",
                                     "build-aux", "ltmain.sh"),
                        os.path.join(_lt_pkg or "", "share", "libtool",
                                     "ltmain.sh")):
                    if _cand and os.path.isfile(_cand):
                        _src = _cand
                        break
            except Exception:
                _src = None
            if _src:
                try:
                    shutil.copy(_src, _dst)
                    self.output.info(
                        "dcap bootstrap: copied ltmain.sh {} -> "
                        "{}".format(_src, _dst))
                except OSError as _exc:
                    self.output.warning(
                        "dcap bootstrap: copy ltmain.sh failed: "
                        "{!r}".format(_exc))
        if not os.path.isfile(os.path.join(self.source_folder, "config",
                                           "ltmain.sh")):
            self.output.warning(
                "dcap bootstrap: config/ltmain.sh still missing after "
                "libtoolize; automake may fail")
        if _aclocal_real:
            _acdir = os.path.join(_automake_root, "share", "aclocal-1.18")
            _sysdir = os.path.join(_automake_root, "share", "aclocal")
            _aclocal_argv = [_perl, _aclocal_real,
                             "--automake-acdir=" + _acdir,
                             "--system-acdir=" + _sysdir]
            for _ad in _extra_acdirs:
                _aclocal_argv.extend(["-I", _ad])
            _aclocal_argv.extend(["-I", "config", "--force"])
            _aclocal_env = {"PERL": _perl,
                            "PERL5LIB": os.path.join(
                                _automake_root, "share", "automake-1.18")}
            if _aclocal_path:
                _aclocal_env["ACLOCAL_PATH"] = _aclocal_path
            self._run(_aclocal_argv,
                      cwd=self.source_folder,
                      extra_env=_aclocal_env)
        else:
            _sys_aclocal = self._system_tool(["aclocal", "aclocal-1.18"])
            if _sys_aclocal is None:
                _sys_aclocal = self._which(["aclocal", "aclocal-1.18"])
            if _sys_aclocal is None:
                raise ConanException(
                    "dcap bootstrap: need aclocal but neither "
                    "conan automake .aclocal-real nor system aclocal found "
                    "(automake_root={})".format(_automake_root))
            self.output.warning(
                "dcap bootstrap: .aclocal-real missing, fallback to "
                "system {}".format(_sys_aclocal))
            _aclocal_lib = os.path.join(
                os.path.dirname(os.path.dirname(_sys_aclocal)),
                "share", "automake-1.18")
            if not os.path.isdir(_aclocal_lib):
                _aclocal_lib = os.path.join(
                    _automake_root, "share", "automake-1.18")
            _sys_aclocal_argv = ["sh", _sys_aclocal]
            for _ad in _extra_acdirs:
                _sys_aclocal_argv.extend(["-I", _ad])
            _sys_aclocal_argv.extend(["-I", "config", "--force"])
            _sys_aclocal_env = {"PERL": _perl, "PERL5LIB": _aclocal_lib}
            if _aclocal_path:
                _sys_aclocal_env["ACLOCAL_PATH"] = _aclocal_path
            self._run(_sys_aclocal_argv,
                      cwd=self.source_folder,
                      extra_env=_sys_aclocal_env)
        _autoheader = _real(_autoconf_root, ["autoheader"])
        if _autoheader is None:
            _autoheader = self._system_tool(["autoheader"]) or \
                self._which(["autoheader"])
        if _autoheader is None:
            raise ConanException(
                "dcap bootstrap: need autoheader but not found "
                "(autoconf_root={})".format(_autoconf_root))
        _ah_lib = os.path.join(
            os.path.dirname(os.path.dirname(_autoheader)),
            "share", "autoconf")
        if not os.path.isdir(_ah_lib):
            _ah_lib = os.path.join(_autoconf_root, "share", "autoconf")
        self.output.info("dcap bootstrap: autoheader={} PERL5LIB={}".format(
            _autoheader, _ah_lib))
        self._run(["sh", _autoheader, "--force"],
                  cwd=self.source_folder,
                  extra_env={"PERL": _perl, "PERL5LIB": _ah_lib})
        if _automake_real:
            _libdir = os.path.join(_automake_root, "share", "automake-1.18")
            self._run([_perl, _automake_real,
                       "--libdir=" + _libdir,
                       "--add-missing", "--copy", "--foreign"],
                      cwd=self.source_folder,
                      extra_env={"PERL": _perl,
                                 "PERL5LIB": os.path.join(
                                     _automake_root, "share", "automake-1.18")})
        else:
            _sys_am = self._system_tool(["automake", "automake-1.18"]) or \
                self._which(["automake", "automake-1.18"])
            if _sys_am is None:
                raise ConanException(
                    "dcap bootstrap: need automake but neither "
                    "conan automake .automake-real nor system automake found "
                    "(automake_root={})".format(_automake_root))
            self.output.warning(
                "dcap bootstrap: .automake-real missing, fallback to "
                "system {}".format(_sys_am))
            _am_lib = os.path.join(
                os.path.dirname(os.path.dirname(_sys_am)),
                "share", "automake-1.18")
            if not os.path.isdir(_am_lib):
                _am_lib = os.path.join(
                    _automake_root, "share", "automake-1.18")
            self._run(["sh", _sys_am, "--add-missing", "--copy", "--foreign"],
                      cwd=self.source_folder,
                      extra_env={"PERL": _perl, "PERL5LIB": _am_lib})
        _autoconf = _real(_autoconf_root, ["autoconf"])
        if _autoconf is None:
            _autoconf = self._system_tool(["autoconf"]) or \
                self._which(["autoconf"])
        if _autoconf is None:
            raise ConanException(
                "dcap bootstrap: need autoconf but not found "
                "(autoconf_root={})".format(_autoconf_root))
        _ac_lib = os.path.join(
            os.path.dirname(os.path.dirname(_autoconf)),
            "share", "autoconf")
        if not os.path.isdir(_ac_lib):
            _ac_lib = os.path.join(_autoconf_root, "share", "autoconf")
        self.output.info("dcap bootstrap: autoconf={} PERL5LIB={}".format(
            _autoconf, _ac_lib))
        self._run(["sh", _autoconf, "--force"],
                  cwd=self.source_folder,
                  extra_env={"PERL": _perl, "PERL5LIB": _ac_lib})

    def _fix_public_header(self):
        # Consumer-visible dcap.h uses off64_t/struct stat64/struct
        # dirent64 unconditionally, with a fallback only for __APPLE__.
        # musl/OHOS provides those *64 names solely as macros to the base
        # types when _GNU_SOURCE/_LARGEFILE64_SOURCE is visible before the
        # system headers; a bare consumer TU (like test_package/test.c)
        # therefore fails with "unknown type name 'off64_t'". Fix here with
        # fail-closed anchors (same strategy as _fix_telnet_passwd, no
        # patch-file hunk accounting): define the feature macros at the top
        # of the header for non-glibc Linux, and add explicit alias
        # fallbacks after the __APPLE__ block for libcs that still hide
        # them (OHOS trims some *64/pwent APIs even with _GNU_SOURCE).
        # glibc path unchanged (guarded by __GLIBC__ exclusion).
        _p = os.path.join(self.source_folder, "src", "dcap.h")
        if not os.path.isfile(_p):
            raise ConanException(
                "dcap public header fix: not found: {}".format(_p))
        with open(_p, "r", encoding="utf-8", errors="replace") as _f:
            _t = _f.read()
        if "#include <sys/types.h>" not in _t:
            raise ConanException(
                "dcap public header fix: anchor '#include <sys/types.h>' missing")
        if "#ifdef __APPLE__" not in _t:
            raise ConanException(
                "dcap public header fix: anchor '#ifdef __APPLE__' missing")
        if "DCAP_MUSL_LFS64_FALLBACK" not in _t:
            _pre = (
                "\n#ifndef _GNU_SOURCE\n"
                "#if defined(__linux__) && !defined(__GLIBC__) && "
                "!defined(__UCLIBC__)\n"
                "#define _GNU_SOURCE 1\n"
                "#endif\n"
                "#endif\n"
                "#ifndef _LARGEFILE64_SOURCE\n"
                "#if defined(__linux__) && !defined(__GLIBC__) && "
                "!defined(__UCLIBC__)\n"
                "#define _LARGEFILE64_SOURCE 1\n"
                "#endif\n"
                "#endif\n"
            )
            _t = _t.replace("#include <stdio.h>", _pre + "#include <stdio.h>", 1)
            _anchor = (
                "#ifdef __APPLE__\n"
                "#define stat64 stat\n"
                "#define off64_t off_t\n"
                "#define dirent64 dirent\n"
                "#endif"
            )
            if _anchor not in _t:
                raise ConanException(
                    "dcap public header fix: anchor '__APPLE__ alias block' missing")
            _fallback = (
                _anchor + "\n"
                "#if defined(__linux__) && !defined(__GLIBC__) && "
                "!defined(__UCLIBC__)\n"
                "/* DCAP_MUSL_LFS64_FALLBACK: musl/OHOS exposes *64 only as macros\n"
                "   to the base types under _GNU_SOURCE/_LARGEFILE64_SOURCE.\n"
                "   Provide the same alias as __APPLE__ for consumers that still\n"
                "   do not see them (strict ISO mode or trimmed OHOS headers).\n"
                "   off_t is always 64-bit on musl/OHOS, so the alias is exact. */\n"
                "#ifndef stat64\n"
                "#define stat64 stat\n"
                "#endif\n"
                "#ifndef off64_t\n"
                "#define off64_t off_t\n"
                "#endif\n"
                "#ifndef dirent64\n"
                "#define dirent64 dirent\n"
                "#endif\n"
                "#endif"
            )
            _t = _t.replace(_anchor, _fallback, 1)
        with open(_p, "w", encoding="utf-8", newline="\n") as _f:
            _f.write(_t)
        self.output.info("dcap public header musl/off64_t fallback injected")

    def _fix_telnet_passwd(self):
        # OHOS libc omits fgetpwent/putpwent even with _GNU_SOURCE
        # (bionic-style trimming); previous patch-file approach failed
        # on hunk accounting, so patch the pristine source directly here
        # with fail-closed anchors. Non-glibc Linux gets file-local
        # passwd-line helpers (differently named to avoid a static vs
        # extern clash on vanilla musl); glibc keeps using libc.
        _p = os.path.join(self.source_folder, "plugins", "telnet",
                          "dcapPasswd.c")
        if not os.path.isfile(_p):
            raise ConanException(
                "dcap telnet fix: not found: {}".format(_p))
        with open(_p, "r", encoding="utf-8", errors="replace") as _f:
            _t = _f.read()
        if "#include <unistd.h>" not in _t:
            raise ConanException(
                "dcap telnet fix: anchor '#include <unistd.h>' missing")
        if "int main" not in _t:
            raise ConanException(
                "dcap telnet fix: anchor 'int main' missing")
        if "_GNU_SOURCE" not in _t.split("int main")[0]:
            _t = _t.replace(
                "#include <unistd.h>",
                "#ifndef _GNU_SOURCE\n#define _GNU_SOURCE 1\n#endif\n"
                "#include <unistd.h>",
                1)
        if "dcap_fgetpwent" not in _t:
            _fallback = (
                "\n#if defined(__linux__) && "
                "!defined(__GLIBC__) && !defined(__UCLIBC__)\n"
                "static char dcap_pw_line[4096];\n"
                "static struct passwd dcap_pw_ent;\n"
                "static struct passwd *dcap_fgetpwent(FILE *stream)\n"
                "{\n"
                "  char *fields[7];\n"
                "  char *sep;\n"
                "  int i;\n"
                "  if (stream == NULL) {\n"
                "    return NULL;\n"
                "  }\n"
                "  if (fgets(dcap_pw_line, (int)sizeof(dcap_pw_line),"
                " stream) == NULL) {\n"
                "    return NULL;\n"
                "  }\n"
                "  i = (int)strlen(dcap_pw_line);\n"
                "  while (i > 0 && (dcap_pw_line[i - 1] == '\\n' || "
                "dcap_pw_line[i - 1] == '\\r')) {\n"
                "    dcap_pw_line[--i] = '\\0';\n"
                "  }\n"
                "  fields[0] = dcap_pw_line;\n"
                "  for (i = 1; i < 7; i++) {\n"
                "    sep = strchr(fields[i - 1], ':');\n"
                "    if (sep == NULL) {\n"
                "      return NULL;\n"
                "    }\n"
                "    *sep = '\\0';\n"
                "    fields[i] = sep + 1;\n"
                "  }\n"
                "  dcap_pw_ent.pw_name = fields[0];\n"
                "  dcap_pw_ent.pw_passwd = fields[1];\n"
                "  dcap_pw_ent.pw_uid ="
                " (uid_t)strtoul(fields[2], NULL, 10);\n"
                "  dcap_pw_ent.pw_gid ="
                " (gid_t)strtoul(fields[3], NULL, 10);\n"
                "  dcap_pw_ent.pw_gecos = fields[4];\n"
                "  dcap_pw_ent.pw_dir = fields[5];\n"
                "  dcap_pw_ent.pw_shell = fields[6];\n"
                "  return &dcap_pw_ent;\n"
                "}\n"
                "static int dcap_putpwent(const struct passwd *pw,"
                " FILE *stream)\n"
                "{\n"
                "  const char *nm = (pw && pw->pw_name) ? pw->pw_name : \"\";\n"
                "  const char *pwd = (pw && pw->pw_passwd)"
                " ? pw->pw_passwd : \"\";\n"
                "  const char *gecos = (pw && pw->pw_gecos)"
                " ? pw->pw_gecos : \"\";\n"
                "  const char *dir = (pw && pw->pw_dir) ? pw->pw_dir : \"\";\n"
                "  const char *sh = (pw && pw->pw_shell)"
                " ? pw->pw_shell : \"\";\n"
                "  if (pw == NULL || stream == NULL) {\n"
                "    return -1;\n"
                "  }\n"
                "  if (fprintf(stream, \"%s:%s:%u:%u:%s:%s:%s\\n\","
                " nm, pwd, (unsigned)pw->pw_uid, (unsigned)pw->pw_gid,"
                " gecos, dir, sh) < 0) {\n"
                "    return -1;\n"
                "  }\n"
                "  return 0;\n"
                "}\n"
                "#define fgetpwent dcap_fgetpwent\n"
                "#define putpwent dcap_putpwent\n"
                "#endif\n\n"
            )
            _t = _t.replace("int main", _fallback + "int main", 1)
        with open(_p, "w", encoding="utf-8", newline="\n") as _f:
            _f.write(_t)
        self.output.info("dcap telnet passwd fallback injected")

    def _fix_tests_include(self):
        # Upstream tests/Makefile.am only has -I$(includedir), so
        # tests/test_url.c (#include "dcap_url.h"/"dcap_types.h", both
        # internal headers living in src/) fails with
        # "fatal error: 'dcap_url.h' file not found" as soon as the
        # library itself compiles. Fixed here with fail-closed anchors
        # (same strategy as _fix_telnet_passwd, no patch-file hunk
        # accounting): prepend -I$(top_srcdir)/src (pristine headers)
        # and -I$(top_builddir)/src (generated src/debug_level.h) ahead
        # of -I$(includedir). Works for in-source and out-of-source
        # (conan Autotools) builds; glibc behaviour unchanged apart
        # from the extra -I.
        _p = os.path.join(self.source_folder, "tests", "Makefile.am")
        if not os.path.isfile(_p):
            raise ConanException(
                "dcap tests fix: not found: {}".format(_p))
        with open(_p, "r", encoding="utf-8", errors="replace") as _f:
            _t = _f.read()
        if "TESTS = test_url" not in _t:
            raise ConanException(
                "dcap tests fix: anchor 'TESTS = test_url' missing")
        if "-I$(includedir)" not in _t:
            raise ConanException(
                "dcap tests fix: anchor '-I$(includedir)' missing")
        if "$(top_srcdir)/src" not in _t:
            _t = _t.replace(
                "-I$(includedir)",
                "-I$(top_srcdir)/src -I$(top_builddir)/src -I$(includedir)",
                1)
        with open(_p, "w", encoding="utf-8", newline="\n") as _f:
            _f.write(_t)
        self.output.info("dcap tests include path fixed")

    def build(self):
        _tmp = self._ensure_tmp_env()
        apply_conandata_patches(self)
        self._fix_public_header()
        self._fix_telnet_passwd()
        self._fix_tests_include()
        self._ensure_tmp_env()
        self._bootstrap()
        _configure = os.path.join(self.source_folder, "configure")
        with open(_configure, "r", encoding="utf-8", errors="replace") as _f:
            _text = _f.read()
        _text = _text.replace("umask 077", "umask 022")
        _text = _text.replace("/data/service/hnp/bin/bash", "/bin/sh")
        with open(_configure, "w", encoding="utf-8", newline="\n") as _f:
            _f.write(_text)
        autotools = Autotools(self)
        try:
            _cfg_args = autotools._configure_args
        except AttributeError:
            _cfg_args = getattr(autotools, "configure_args", "")
        _cc = self._resolve_cc()
        _make = self._resolve_make()
        self.output.info("dcap configure: CC={} MAKE={} TMPDIR={}".format(
            _cc, _make, _tmp))
        try:
            self._run([_cc, "--version"], cwd=self.build_folder)
        except ConanException as _exc:
            self.output.warning("dcap CC --version failed: {!r}".format(_exc))
        _cfg_path = _configure.replace("\\", "/")
        _args = shlex.split(str(_cfg_args)) if str(_cfg_args).strip() else []
        # Manual list-form configure bypasses Autotools.configure(), which is
        # what normally appends --prefix=<package_folder>. A bare configure
        # falls back to prefix "/" here (preflight evidence: install tried
        # //lib and //share on the read-only root). Filter out every
        # install-location override the toolchain may have carried in
        # (a later --prefix wins in autoconf, so merely prepending when
        # missing is not enough) and append a single correct prefix last
        # (zzuf precedent: plain `make install` with empty DESTDIR installs
        # into package_folder).
        _pkg_prefix = str(self.package_folder).replace("\\", "/")
        _drop = ("--prefix=", "--exec-prefix=", "--bindir=", "--sbindir=",
                 "--libexecdir=", "--libdir=", "--datadir=", "--datarootdir=",
                 "--sysconfdir=", "--localstatedir=", "--includedir=",
                 "--oldincludedir=", "--docdir=", "--infodir=", "--htmldir=",
                 "--dvidir=", "--pdfdir=", "--psdir=", "--mandir=",
                 "--with-doc-dir=", "--with-rpm-dir=", "--with-tunneldir=")
        _kept = [str(_a) for _a in _args
                 if not str(_a).startswith(_drop)]
        _dropped = [str(_a) for _a in _args
                    if str(_a).startswith(_drop)]
        if _dropped:
            self.output.info("dcap configure: dropped location args: "
                             + " ".join(_dropped))
        _args = _kept + ["--prefix=" + _pkg_prefix,
                         "--with-doc-dir=" + _pkg_prefix
                         + "/share/doc/dcap-2.47.14"]
        self.output.info("dcap configure args: " + " ".join(_args))
        try:
            self._run(["sh", _cfg_path] + _args, cwd=self.build_folder,
                      extra_env={"CC": _cc, "DESTDIR": "", "DOCD": "",
                                 "RPMD": str(self.build_folder)})
        except ConanException:
            for _log in (os.path.join(self.build_folder, "config.log"),):
                if os.path.isfile(_log):
                    try:
                        with open(_log, "r", encoding="utf-8", errors="replace") as _f:
                            _t = _f.read()
                        self.output.info("dcap config.log tail:\n" + _t[-6000:])
                    except OSError:
                        pass
            raise
        # Fail fast if configure still locked a root prefix: read it back
        # from the generated Makefiles instead of waiting for //lib errors
        # at `make install` time.
        for _mf in (os.path.join(self.build_folder, "src", "Makefile"),
                    os.path.join(self.build_folder, "Makefile")):
            try:
                with open(_mf, "r", encoding="utf-8",
                           errors="replace") as _f:
                    _mt = _f.read()
                _m = re.search(r"^prefix\s*=\s*(\S+)\s*$", _mt, re.M)
                if _m:
                    self.output.info("dcap configured prefix ({}): {}".format(
                        os.path.basename(os.path.dirname(_mf)), _m.group(1)))
                    if _m.group(1).strip().rstrip("/") in ("", "//"):
                        raise ConanException(
                            "dcap configure kept root prefix {!r} in {}; "
                            "args were: {}".format(_m.group(1), _mf, _args))
            except ConanException:
                raise
            except OSError:
                pass
        self._run([_make, "-j1"], cwd=self.build_folder)
        try:
            self._run([_make, "-j1", "check"], cwd=self.build_folder)
            _check_rc = 0
        except ConanException:
            _check_rc = 1
        _result = self._parse_upstream_results()
        self._emit_upstream_result(_result)
        if _check_rc != 0 or _result["status"] != "passed":
            raise ConanException(
                "dcap upstream tests failed (make check rc={}, marker={})".format(
                    _check_rc, _result))

    def _emit_upstream_result(self, result):
        # Dual-channel evidence (cld2 precedent): keep the original
        # self.output.info channel and append a stdout-direct print of the
        # same line, then persist to a real file so a later Conan cache hit
        # (build() skipped) can still re-emit from test_package. No BOM.
        _line = ("HMBS_UPSTREAM_TEST_RESULT="
                 + json.dumps(result, ensure_ascii=False))
        self.output.info(_line)
        try:
            print(_line, flush=True)
        except Exception:
            pass
        try:
            _p = os.path.join(str(self.build_folder), "hmbs_upstream.json")
            with open(_p, "w", encoding="utf-8", newline="\n") as _f:
                _f.write(json.dumps(result, ensure_ascii=False))
        except OSError as _exc:
            self.output.warning(
                "dcap upstream persist failed: {!r}".format(_exc))

    def _parse_upstream_results(self):
        _log = None
        for _cand in (os.path.join(self.build_folder, "tests", "test-suite.log"),
                      os.path.join(self.source_folder, "tests", "test-suite.log")):
            if os.path.isfile(_cand):
                _log = _cand
                break
        _base = {"framework": "cunit", "command": "make check",
                 "discovered": 11, "executed": 0,
                 "passed": 0, "failed": 0, "skipped": 0}
        if _log is None:
            _base.update({"status": "failed",
                          "reason": "tests/test-suite.log not generated"})
            return _base
        try:
            with open(_log, "r", encoding="utf-8", errors="replace") as _f:
                _text = _f.read()
        except OSError as _exc:
            _base.update({"status": "failed",
                          "reason": "cannot read test-suite.log: {!r}".format(_exc)})
            return _base
        if not _text.strip():
            _base.update({"status": "failed",
                          "reason": "tests/test-suite.log is empty"})
            return _base
        _counts = {}
        for _name in ("TOTAL", "PASS", "XFAIL", "FAIL", "XPASS", "SKIP", "ERROR"):
            _m = re.search(r"^# {}:\s*(\d+)\s*$".format(_name), _text, re.M)
            _counts[_name] = int(_m.group(1)) if _m else 0
        _total = _counts["TOTAL"]
        _passed = _counts["PASS"] + _counts["XFAIL"]
        _failed = _counts["FAIL"] + _counts["XPASS"] + _counts["ERROR"]
        _skipped = _counts["SKIP"]
        # Prefer the real CUnit case counts when the Run Summary is present:
        # automake counts test programs (TOTAL=1 for the single test_url
        # binary) while the audit/PR口径 counts the 11 CU_add_test cases
        # inside it. Parse the "tests Total Ran Passed Failed Inactive" row.
        _cu = re.search(
            r"^\s*tests\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)(?:\s+(\d+))?\s*$",
            _text, re.M | re.I)
        if _cu:
            try:
                _cu_total = int(_cu.group(1))
                _cu_ran = int(_cu.group(2))
                _cu_passed = int(_cu.group(3))
                _cu_failed = int(_cu.group(4))
                _cu_inactive = int(_cu.group(5)) if _cu.group(5) is not None else 0
                if _cu_total > 0:
                    _base.update({"discovered": _cu_total,
                                  "executed": _cu_ran,
                                  "passed": _cu_passed,
                                  "failed": _cu_failed,
                                  "skipped": _cu_inactive})
                    if (_cu_failed > 0 or _cu_inactive > 0
                            or _cu_ran != _cu_total
                            or _cu_passed != _cu_total):
                        _base.update({"status": "failed",
                                      "reason": "CUnit summary tests {}/{}/{} "
                                      "failed/inactive mismatch; log tail: {}"
                                      .format(_cu_total, _cu_ran, _cu_passed,
                                              _text.strip()[-500:])})
                    elif _failed > 0 or _total <= 0:
                        _base.update({"status": "failed",
                                      "reason": "automake harness failed "
                                      "despite CUnit 11/11; log tail: {}"
                                      .format(_text.strip()[-500:])})
                    else:
                        _base.update({"status": "passed"})
                    return _base
            except ValueError:
                pass
        _base.update({"discovered": _total, "executed": _passed + _failed,
                      "passed": _passed, "failed": _failed, "skipped": _skipped})
        if _total <= 0:
            _base.update({"status": "failed",
                          "reason": "TOTAL is 0: harness ran no tests"})
        elif _failed > 0 or _skipped > 0 or _base["executed"] != _total:
            _base.update({"status": "failed",
                          "reason": "log tail: {}".format(_text.strip()[-500:])})
        else:
            _base.update({"status": "passed"})
        return _base

    def package(self):
        _tmp = self._ensure_tmp_env()
        self.output.info("dcap package: TMPDIR={} package_folder={}".format(
            _tmp, str(self.package_folder).replace("\\", "/")))
        _make = self._resolve_make()
        # Prefix was forced to package_folder at configure time, so install
        # must run with empty DESTDIR (zzuf precedent: plain `make install`).
        # An inherited DESTDIR (e.g. "/") would rebase paths to //lib.
        # Diagnose what automake generated: device `make install` exits 0
        # yet has landed only libLTLIBRARIES, so log the install primaries.
        for _mf in (os.path.join(self.build_folder, "src", "Makefile"),
                    os.path.join(self.build_folder, "Makefile")):
            try:
                with open(_mf, "r", encoding="utf-8",
                          errors="replace") as _f:
                    _mt = _f.read()
            except OSError:
                continue
            _tag = os.path.basename(os.path.dirname(_mf)) or "top"
            for _key in ("prefix", "bindir", "includedir", "SUBDIRS",
                         "bin_PROGRAMS", "lib_LTLIBRARIES",
                         "library_include_HEADERS", "library_includedir"):
                _m = re.search(r"^" + _key + r"\s*=\s*(.*)$", _mt, re.M)
                self.output.info("dcap install primary {} ({}): {!r}".format(
                    _key, _tag,
                    _m.group(1).strip() if _m else "<absent>"))
        self._run([_make, "install", "DESTDIR="], cwd=self.build_folder)
        for _root, _dirs, _files in os.walk(os.path.join(self.package_folder, "lib")):
            for _fn in _files:
                if _fn.endswith(".la"):
                    os.remove(os.path.join(_root, _fn))
        # lib repair (preflight evidence 2026-09-11: package() reported
        # libdcap.so + libdcap.so.1 packaged, yet test_package
        # `clang ... -L<package>/lib -ldcap` failed with
        # `ld.lld: error: unable to find library -ldcap`).
        # Typical libtool layout is a symlink chain
        # libdcap.so -> libdcap.so.1 -> libdcap.so.1.1.47 (real ELF in
        # src/.libs); if the versioned target never reached <pkg>/lib
        # (or HMDFS dropped the symlink), -ldcap cannot resolve even
        # though the .so name appears in the package listing.
        # Materialize every libdcap/libpdcap soname entry as a real file
        # (symlink -> byte copy) so the linker never follows a dangling
        # link. Python-level copies only, no shell/install(1).
        _lib_dir = os.path.join(str(self.package_folder), "lib")
        _dotlibs = os.path.join(str(self.build_folder), "src", ".libs")
        try:
            _entries = sorted(os.listdir(_lib_dir)) if os.path.isdir(_lib_dir) else []
            for _e in _entries:
                _p = os.path.join(_lib_dir, _e)
                try:
                    _st = os.lstat(_p)
                    import stat as _stat
                    if _stat.S_ISLNK(_st.st_mode):
                        try:
                            _tgt = os.readlink(_p)
                        except OSError:
                            _tgt = "<unreadable>"
                        _ok = os.path.isfile(_p)
                        self.output.info(
                            "dcap package lib entry: {} -> {} (dangling={})".format(
                                _e, _tgt, (not _ok)))
                    else:
                        self.output.info(
                            "dcap package lib entry: {} ({} bytes)".format(
                                _e, _st.st_size))
                except OSError as _exc:
                    self.output.warning(
                        "dcap package lib stat failed for {}: {!r}".format(_e, _exc))
        except OSError as _exc:
            self.output.warning("dcap package lib list failed: {!r}".format(_exc))
        for _lib in ("libdcap", "libpdcap"):
            try:
                _cands = []
                if os.path.isdir(_dotlibs):
                    for _f in sorted(os.listdir(_dotlibs)):
                        if _f.startswith(_lib + ".so"):
                            _cands.append(_f)
                _pkg_files = set(os.listdir(_lib_dir)) if os.path.isdir(_lib_dir) else set()
                for _f in _cands:
                    _dst = os.path.join(_lib_dir, _f)
                    _needs = False
                    if _f not in _pkg_files:
                        _needs = True
                    elif not os.path.isfile(_dst):
                        # Dangling symlink: lstat exists but open fails.
                        _needs = True
                    if _needs:
                        _src = os.path.join(_dotlibs, _f)
                        try:
                            with open(_src, "rb") as _rf:
                                _data = _rf.read()
                            if not _data:
                                self.output.warning(
                                    "dcap package: skip empty build lib {}".format(_src))
                                continue
                            try:
                                if os.path.lexists(_dst):
                                    os.remove(_dst)
                            except OSError:
                                pass
                            with open(_dst, "wb") as _wf:
                                _wf.write(_data)
                            self.output.info(
                                "dcap package: materialized {} ({} bytes from .libs)".format(
                                    _f, len(_data)))
                        except OSError as _exc:
                            self.output.warning(
                                "dcap package: copy lib {} failed: {!r}".format(_f, _exc))
                # Ensure the bare -l name (libX.so) is a real readable file.
                _so = os.path.join(_lib_dir, _lib + ".so")
                if not os.path.isfile(_so):
                    _fallbacks = sorted(
                        [f for f in (os.listdir(_lib_dir) if os.path.isdir(_lib_dir) else [])
                         if f.startswith(_lib + ".so.")],
                        key=len, reverse=True)
                    _done = False
                    for _fb in _fallbacks:
                        _fp = os.path.join(_lib_dir, _fb)
                        if not os.path.isfile(_fp):
                            continue
                        try:
                            with open(_fp, "rb") as _rf:
                                _data = _rf.read()
                            if not _data:
                                continue
                            try:
                                if os.path.lexists(_so):
                                    os.remove(_so)
                            except OSError:
                                pass
                            with open(_so, "wb") as _wf:
                                _wf.write(_data)
                            self.output.info(
                                "dcap package: lib fallback {} -> copy of {} ({} bytes)".format(
                                    _lib + ".so", _fb, len(_data)))
                            _done = True
                            break
                        except OSError as _exc:
                            self.output.warning(
                                "dcap package: fallback copy {} failed: {!r}".format(_fb, _exc))
                    if not _done:
                        self.output.warning(
                            "dcap package: no usable versioned file to back {}".format(
                                _lib + ".so"))
            except OSError as _exc:
                self.output.warning(
                    "dcap package: lib repair for {} failed: {!r}".format(_lib, _exc))
        try:
            _final = sorted(os.listdir(_lib_dir)) if os.path.isdir(_lib_dir) else []
            _usable = [f for f in _final
                       if f.startswith("libdcap.so") and os.path.isfile(os.path.join(_lib_dir, f))]
            self.output.info("dcap package lib final: {}".format(_final))
            if not _usable:
                _tree = []
                for _proot, _pdirs, _pfiles in os.walk(str(self.package_folder)):
                    _rel = os.path.relpath(_proot, str(self.package_folder))
                    if _rel.count(os.sep) > 3 or len(_tree) > 60:
                        del _pdirs[:]
                        continue
                    for _fn in sorted(_pfiles)[:20]:
                        _tree.append(os.path.join(_rel, _fn))
                raise ConanException(
                    "dcap package: no usable libdcap.so* file under {}; tree: {}".format(
                        _lib_dir, _tree))
        except ConanException:
            raise
        except OSError as _exc:
            self.output.warning("dcap package lib final check failed: {!r}".format(_exc))
        # `make install` on the device demonstrably drops non-library
        # outputs (headers/bins/data missing despite rc=0), so take explicit
        # ownership of the documented layout with Conan copy (python-level,
        # no install(1)/shell involved): h_sources -> <pkg>/include mirrors
        # library_include_HEADERS; built dccp -> <pkg>/bin mirrors
        # install-binPROGRAMS (best effort: the real ELF lives under
        # src/.libs, the src/dccp path is a libtool wrapper script).
        for _h in ("dcap.h", "dcap_errno.h", "dc_hack.h"):
            _hs = os.path.join(self.source_folder, "src", _h)
            if not os.path.isfile(_hs):
                raise ConanException(
                    "dcap package: upstream header missing from source: "
                    "{}".format(_hs))
            copy(self, _h, src=os.path.join(self.source_folder, "src"),
                 dst=os.path.join(self.package_folder, "include"))
        _dccp = os.path.join(self.build_folder, "src", ".libs", "dccp")
        if os.path.isfile(_dccp):
            copy(self, "dccp", src=os.path.join(self.build_folder, "src", ".libs"),
                 dst=os.path.join(self.package_folder, "bin"))
        else:
            self.output.warning(
                "dcap package: built dccp not found at {}; "
                "bin/ left empty".format(_dccp))
        # Fail fast if the public headers never reached the package folder:
        # upstream installs h_sources (dcap.h/dcap_errno.h/dc_hack.h) to
        # $(includedir), and the consumer test compiles against it.
        _inc_dir = os.path.join(str(self.package_folder), "include")
        _missing = [h for h in ("dcap.h", "dcap_errno.h", "dc_hack.h")
                    if not os.path.isfile(os.path.join(_inc_dir, h))]
        if _missing:
            _tree = []
            for _proot, _pdirs, _pfiles in os.walk(str(self.package_folder)):
                _rel = os.path.relpath(_proot, str(self.package_folder))
                if _rel.count(os.sep) > 3 or len(_tree) > 60:
                    del _pdirs[:]
                    continue
                for _fn in sorted(_pfiles)[:20]:
                    _tree.append(os.path.join(_rel, _fn))
            raise ConanException(
                "dcap package: public headers missing {} under {}; "
                "package tree: {}".format(_missing, _inc_dir, _tree))
        # Persist the real upstream result into the package so test_package
        # can re-emit it every round even when Conan hits the binary cache
        # and build() is skipped (evidence gate requires a marker per run).
        try:
            _src_json = os.path.join(str(self.build_folder),
                                     "hmbs_upstream.json")
            if os.path.isfile(_src_json):
                with open(_src_json, "r", encoding="utf-8") as _rf:
                    _payload = _rf.read()
                # Validate before shipping: must be non-empty legal JSON
                # with a positive discovered count.
                _obj = json.loads(_payload)
                if not isinstance(_obj, dict) or int(_obj.get("discovered", 0)) <= 0:
                    raise ValueError("discovered must be > 0")
                _res_dir = os.path.join(str(self.package_folder), "res")
                os.makedirs(_res_dir, exist_ok=True)
                with open(os.path.join(_res_dir, "hmbs_upstream.json"),
                          "w", encoding="utf-8", newline="\n") as _wf:
                    _wf.write(json.dumps(_obj, ensure_ascii=False))
                self.output.info("dcap package: persisted hmbs_upstream.json")
            else:
                self.output.warning(
                    "dcap package: hmbs_upstream.json not found in build "
                    "folder; test_package cannot re-emit upstream evidence")
        except (OSError, ValueError) as _exc:
            self.output.warning(
                "dcap package: persist upstream evidence failed: {!r}".format(_exc))

    def package_info(self):
        self.cpp_info.libs = ["dcap"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.system_libs = ["pthread", "dl"]
        self.cpp_info.set_property("cmake_file_name", "dcap")
        self.cpp_info.set_property("cmake_target_name", "dcap::dcap")
