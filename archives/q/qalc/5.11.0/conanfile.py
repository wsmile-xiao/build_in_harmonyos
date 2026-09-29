#!/usr/bin/env python3
"""Conan recipe — qalc 5.11.0 (Autotools, application package).

qalc is the Qalculate! command-line calculator.  The upstream release is the
libqalculate source tarball, which builds the library and the qalc CLI from
the same tree (this mirrors Debian/Ubuntu, whose "qalculate" binary package
is produced from the libqalculate source package).  This package therefore
builds libqalculate 5.11.0 and ships bin/qalc together with the lib and its
runtime definition data (share/qalculate).

OHOS adaptation (port of the merged libqalculate 5.8.2-r0 recipe):
- config.guess: HarmonyOS detection (aarch64:HarmonyOS -> aarch64-unknown-linux-gnu)
- configure: drop `umask 077` temp-dir guards (HMDFS restriction)
- util.cc: pthread_cancel family guarded by feature-detected HAVE_PTHREAD_*
  macros (OHOS musl does not provide them); pthread_compat.h is generated in
  build() with -Werror=implicit-function-declaration detection
- intltool is gone in 5.11.0; data XMLs are generated with GNU msgfmt --xml
  (NLS path), so only msgfmt is needed as a build tool

Pitfalls inherited from 5.8.2-r0 (both locally reproduced):
- Do NOT use AutotoolsDeps/VirtualRunEnv: AutotoolsDeps pollutes LIBS so even
  the early cross-compiling conftest links conan deps it cannot run; the
  VirtualRunEnv LD_LIBRARY_PATH ordering hijacks lld's own SDK libxml2 with
  the conan libxml2 (same SONAME, different symbol set) -> "Error relocating
  lld".  Inject dependency -I/-L flags manually instead.
- LD_LIBRARY_PATH must be injected directly into os.environ inside build():
  build-time C++ tools need libc++_shared.so and the SDK lld needs its own
  libxml2.so.16 *before* the conan dependency dirs.
- Dependency .la files carry libdir='//lib'; libtool then fails to resolve
  them when creating libqalculate.la.  Fix them cross-package (mpfr.la's
  dependency on libgmp.la must resolve to the gmp package's real lib dir).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout

# cmd-pkgs prefix on the CI worker (tools are preinstalled there)
GTK_PREFIX = os.path.expanduser("~/usr/local")

# Build tool needed by the NLS data path (msgfmt --xml).  Only downloaded from
# cmd-pkgs when the environment does not provide a runnable msgfmt (the CI
# worker has it at ~/usr/local; the macOS dev box uses Homebrew gettext).
GETTEXT_VERSION = "0.22.5"


class QalcConan(ConanFile):
    name = "qalc"
    version = "5.11.0"
    description = ("Qalculate! command-line calculator with arbitrary "
                   "precision, symbolic calculation and unit conversion")
    license = "GPL-2.0-or-later"
    homepage = "https://qalculate.github.io/"
    url = "https://github.com/Qalculate/libqalculate"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # configure.ac hard-errors on gmp/mpfr (AC_CHECK_LIB) and libxml-2.0
        # (PKG_CHECK_MODULES); readline enhances the qalc CLI.  All published
        # in the ohpcd registry.
        self.requires("gmp/6.3.0")
        self.requires("mpfr/4.2.2")
        self.requires("libxml2/2.15.3")
        self.requires("readline/8.3")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # libxml-2.0.pc for configure's PKG_CHECK_MODULES
        PkgConfigDeps(self).generate()

        tc = AutotoolsToolchain(self)
        # Optional deps not published in the registry -> disabled
        tc.configure_args.append("--without-libcurl")
        tc.configure_args.append("--without-icu")
        # Explicit triplets (wdiff/zeitgeist pattern): when the same OHOS
        # profile serves as both -pr:h and -pr:b (ohos-local verification),
        # conan treats the build as native and omits --host, so configure
        # tries to RUN its OHOS conftest on the macOS host and dies with
        # "cannot run C compiled programs".  Upstream 5.11.0 config.sub
        # already accepts linux-ohos*, no config.sub patch needed.
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        # Manual dependency flag injection (see module docstring: no
        # AutotoolsDeps, no VirtualRunEnv)
        _env = tc.environment()
        for _ref, _dep in self.dependencies.items():
            _inc = " ".join("-I{}".format(_d)
                            for _d in (_dep.cpp_info.includedirs or [])
                            if os.path.isabs(_d))
            if _inc:
                _env.prepend("CPPFLAGS", _inc)
                _env.prepend("CXXFLAGS", _inc)
                _env.prepend("CFLAGS", _inc)
            _lp = " ".join("-L{}".format(_d)
                           for _d in (_dep.cpp_info.libdirs or [])
                           if os.path.isabs(_d))
            if _lp:
                _env.prepend("LDFLAGS", _lp)
        tc.generate(_env)

    def _install_cmd_pkg(self, name, version, prefix, marker):
        """Download a precompiled tool from cmd-pkgs (CI worker fallback)."""
        import ssl
        import tarfile
        import urllib.request
        from io import BytesIO
        if os.path.isfile(os.path.join(prefix, marker)):
            return
        fname = f"{name}-{version}-ohos-aarch64.tar.gz"
        url = ("https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/"
               f"download/pkgs/{fname}")
        self.output.info(f"Installing {name} {version} from cmd-pkgs")
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(url, context=ctx, timeout=600) as resp:
            data = resp.read()
        with tarfile.open(fileobj=BytesIO(data), mode="r:gz") as tf:
            os.makedirs(prefix, exist_ok=True)
            tf.extractall(prefix)

    def _ensure_msgfmt(self):
        """5.11.0 generates data XML with `msgfmt --xml` (intltool is gone).

        Prefer a msgfmt already runnable in PATH (macOS Homebrew gettext);
        only fall back to the cmd-pkgs gettext on the OHOS CI worker.
        """
        if shutil.which("msgfmt"):
            self.output.info("msgfmt found in PATH")
            return
        marker = os.path.join(GTK_PREFIX, "bin", "msgfmt")
        if os.path.isfile(marker):
            self.output.info(f"msgfmt already installed at {GTK_PREFIX}")
            return
        self._install_cmd_pkg("gettext", GETTEXT_VERSION, GTK_PREFIX,
                              "bin/msgfmt")

    def _write_pthread_compat(self):
        """Feature-detect pthread_cancel family (absent on OHOS musl).

        The detection compile must use -Werror=implicit-function-declaration:
        OHOS headers do not declare pthread_cancel, C only warns about the
        implicit declaration, and without -Werror the probe would wrongly
        report the functions as available.
        """
        src = os.path.join(self.source_folder, "libqalculate")
        os.makedirs(src, exist_ok=True)
        test_c = (
            '#include <pthread.h>\n'
            'int main(){pthread_cancel(0);'
            'pthread_setcancelstate(0,0);'
            'pthread_setcanceltype(0,0);return 0;}\n'
        )
        test_file = os.path.join(self.build_folder, "_pthread_test.c")
        header = os.path.join(src, "pthread_compat.h")
        with open(test_file, "w") as f:
            f.write(test_c)
        try:
            self.run(f"$CC -Werror=implicit-function-declaration -c "
                     f"{test_file} -o /dev/null 2>/dev/null",
                     env="conanbuild")
            with open(header, "w") as f:
                f.write("#pragma once\n")
                f.write("#define HAVE_PTHREAD_CANCEL 1\n")
                f.write("#define HAVE_PTHREAD_SETCANCELSTATE 1\n")
                f.write("#define HAVE_PTHREAD_SETCANCELTYPE 1\n")
            self.output.info("pthread_cancel available -> HAVE_PTHREAD_* on")
        except Exception:
            with open(header, "w") as f:
                f.write("#pragma once\n")
                f.write("/* pthread_cancel not available on this platform */\n")
            self.output.info("pthread_cancel unavailable -> HAVE_PTHREAD_* off")

    def _fix_la_files(self):
        """Repair dependency .la files (libdir='//lib' and cross references).

        A dependency .la referenced by another .la (mpfr.la -> libgmp.la) must
        resolve to the package that really owns it, so build a basename ->
        real-path registry first and rewrite every //lib/<basename> reference.
        """
        import re as _re
        la_registry = {}
        for _ref, _dep in self.dependencies.items():
            dep_pkg = _dep.package_folder
            if not dep_pkg:
                continue
            dep_lib = os.path.join(dep_pkg, "lib")
            if not os.path.isdir(dep_lib):
                continue
            for la_name in os.listdir(dep_lib):
                if la_name.endswith(".la"):
                    la_registry[la_name] = os.path.join(dep_lib, la_name)
        for la_path in la_registry.values():
            with open(la_path, "r", encoding="utf-8", errors="replace") as f:
                lac = f.read()
            own_lib = os.path.dirname(la_path)
            fixed = lac.replace("libdir='//lib'", f"libdir='{own_lib}'")
            for base, real in la_registry.items():
                fixed = fixed.replace(f"//lib/{base}", real)
                if not real.startswith(own_lib):
                    fixed = fixed.replace(f"{own_lib}/{base}", real)
            if fixed != lac:
                with open(la_path, "w", encoding="utf-8") as f:
                    f.write(fixed)
                self.output.info(f"patched {os.path.basename(la_path)}: "
                                 f"libdir/deps -> {own_lib}")

    def _soname_la_ldflags(self):
        """libqalculate_la_LDFLAGS with an explicit SONAME appended."""
        import re as _re
        makefile = None
        for cand in (os.path.join(self.build_folder, "libqalculate", "Makefile"),
                     os.path.join(self.build_folder, "build-release",
                                  "libqalculate", "Makefile")):
            if os.path.isfile(cand):
                makefile = cand
                break
        if makefile is None:
            raise Exception("libqalculate/Makefile not found after configure")
        with open(makefile, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        def _var(name):
            m = _re.search(r"^%s\s*=\s*(\S+)" % name, content, _re.M)
            return int(m.group(1)) if m else None
        current, revision, age = (_var("QALCULATE_CURRENT"),
                                  _var("QALCULATE_REVISION"),
                                  _var("QALCULATE_AGE"))
        if None in (current, revision, age):
            raise Exception("QALCULATE_* version-info variables not found")
        major = current - age
        return ("-version-info %d:%d:%d -no-undefined "
                "-Wl,-soname,libqalculate.so.%d" % (current, revision, age, major))

    def build(self):
        self._ensure_msgfmt()
        self._write_pthread_compat()
        apply_conandata_patches(self)
        self._fix_la_files()

        # LD_LIBRARY_PATH for build-time tools (see module docstring):
        # SDK llvm/lib must come *before* conan dependency dirs (lld needs its
        # own libxml2), then the system libc++ dirs, then conan deps.
        import itertools as _it
        sdk_llvm_lib = ("/data/service/hnp/ohos-sdk.org/"
                        "ohos-sdk_26.0.0.18/ohos/native/llvm/lib")
        sdk_ohos_lib = os.path.join(sdk_llvm_lib, "aarch64-linux-ohos")
        _lib_dirs = [sdk_llvm_lib, sdk_ohos_lib, "/system/lib64", "/system/lib"]
        for _ref, _dep in self.dependencies.items():
            for _lp in (_dep.cpp_info.libdirs or []):
                if os.path.isabs(_lp) and _lp not in _lib_dirs:
                    _lib_dirs.append(_lp)
        _prev = os.environ.get("LD_LIBRARY_PATH", "")
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(
            list(_it.chain(_lib_dirs, ([_prev] if _prev else []))))
        self.output.info("LD_LIBRARY_PATH=" + os.environ["LD_LIBRARY_PATH"])

        # PKG_CONFIG_PATH for PkgConfigDeps output + dependency .pc dirs
        _pkg_dirs = []
        for _ref, _dep in self.dependencies.items():
            for _lp in (_dep.cpp_info.libdirs or []):
                if os.path.isabs(_lp):
                    _pkg_dirs.append(os.path.join(_lp, "pkgconfig"))
        os.environ["PKG_CONFIG_PATH"] = os.pathsep.join(_pkg_dirs)
        self.output.info("PKG_CONFIG_PATH=" + os.environ["PKG_CONFIG_PATH"])

        autotools = Autotools(self)
        autotools.configure()

        # libtool 2.6 with a non-GNU-ld linker (clang/lld on OHOS) omits
        # -Wl,-soname, so the linker records the raw relative library path
        # (../libqalculate/.libs/libqalculate.so) in qalc's DT_NEEDED instead
        # of the SONAME (E537 family: not relocatable, breaks at runtime).
        # Inject the SONAME for the library target only, computed from the
        # same -version-info libtool uses (major = current - age).
        la_ldflags = self._soname_la_ldflags()
        self.output.info("libqalculate_la_LDFLAGS=" + la_ldflags)
        autotools.make(args=["-j1", 'libqalculate_la_LDFLAGS="%s"' % la_ldflags])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # libtool .la files bake absolute paths -> not relocatable, remove
        for la in ("lib/libqalculate.la",):
            la_path = os.path.join(self.package_folder, la)
            if os.path.exists(la_path):
                os.unlink(la_path)
                self.output.info(f"removed {la}")

    def package_info(self):
        # The package ships the CLI plus the library it was built from, so
        # downstream consumers may link against it directly.
        # Application package: expose the CLI bindir (code-style rule 4) and
        # the co-packaged library for downstream consumers.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = ["qalculate"]
        self.cpp_info.system_libs = ["pthread"]
        self.cpp_info.requires = ["gmp::gmp", "mpfr::mpfr",
                                  "libxml2::libxml2", "readline::readline"]
