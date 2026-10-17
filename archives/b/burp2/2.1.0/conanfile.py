#!/usr/bin/env python3
"""Conan recipe for burp2 2.1.0 (Burp - Backup and Restore Program).

Adapted for HarmonyOS PC (aarch64-*-ohos) with the OHOS-PC toolchain.
"""
from conan import ConanFile
from conan.tools.files import get, patch, copy, chdir, apply_conandata_patches
from conan.tools.env import VirtualBuildEnv
from conan.tools.layout import basic_layout
from conan.errors import ConanInvalidConfiguration
import os


class Burp2Conan(ConanFile):
    name = "burp2"
    version = "2.1.0"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    license = "AGPL-3.0-only"
    homepage = "https://burp.grke.org/"
    url = "https://github.com/grke/burp"
    description = "Burp is a network backup and restore program (2.x)."
    topics = ("backup", "restore", "network", "burp")
    exports_sources = "patches/*", "conandata.yml"

    def requirements(self):
        self.requires("openssl/3.5.6")
        self.requires("zlib/1.3.1")
        self.requires("librsync/2.3.4")
        self.requires("uthash/2.3.0")
        self.requires("ncurses/6.5")
        self.requires("check/0.15.2")

    def build_requirements(self):
        # Autotools bootstrap; CI workers do not have these pre-installed in
        # the system PATH. NOTE: do NOT add a perl tool_require - the conan
        # perl/5.42.2 package is cross-compiled for OHOS and its Cwd.so cannot
        # be dlopen'd on the same-arch build machine; we use the system perl
        # (/data/service/hnp/bin/perl) instead, like the avimetaedit recipe.
        self.tool_requires("autoconf/2.72")
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")
        self.tool_requires("pkgconf/3.0.5")

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        from conan.tools.files import export_conandata_patches
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        # AutotoolsToolchain emits conanbuild.sh with CPPFLAGS/LDFLAGS/LIBS
        # pointing at the requirements' include/lib dirs, which configure
        # needs to find openssl/zlib/librsync/etc.
        from conan.tools.gnu import AutotoolsToolchain
        tc = AutotoolsToolchain(self)
        tc.generate()
        VirtualBuildEnv(self).generate()

    def _patch_sources(self):
        # Apply recipe patches declared in conandata.yml (G1 gate requires
        # an apply_conandata_patches invocation in the recipe).
        apply_conandata_patches(self)

    def _patch_config_guess_sub(self, aux_dir):
        """Make the generated config.guess/config.sub recognize OHOS/HarmonyOS.

        automake 1.18 (from tool_requires) ships config.guess/config.sub that
        do not know the `aarch64:...:HarmonyOS` triplet, so configure's
        `checking build system type` fails with "unable to guess system type".
        Insert an early OHOS identification branch in config.guess and allow
        the aarch64-ohos OS in config.sub.
        """
        import re
        cg = os.path.join(aux_dir, "config.guess")
        if os.path.isfile(cg):
            with open(cg, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            if "OHOS-PC adaptation" not in content:
                marker = "case $UNAME_MACHINE:$UNAME_SYSTEM:$UNAME_RELEASE:$UNAME_VERSION in"
                patch_txt = (
                    "# ---- OHOS-PC adaptation: identify HarmonyOS/OHOS early ----\n"
                    "case \"$UNAME_SYSTEM\" in\n"
                    "  HarmonyOS|OHOS|OpenHarmony)\n"
                    "    case \"$UNAME_MACHINE\" in\n"
                    "      aarch64|arm64) echo \"aarch64-unknown-linux-ohos\"; exit 0 ;;\n"
                    "      armv7*) echo \"arm-unknown-linux-ohos-eabi\"; exit 0 ;;\n"
                    "      *) echo \"$UNAME_MACHINE-unknown-linux-ohos\"; exit 0 ;;\n"
                    "    esac ;;\n"
                    "esac\n"
                    "# ---- end OHOS-PC adaptation ----\n"
                )
                if marker in content:
                    content = content.replace(marker, patch_txt + marker, 1)
                    with open(cg, "w", encoding="utf-8") as f:
                        f.write(content)
        cs = os.path.join(aux_dir, "config.sub")
        if os.path.isfile(cs):
            with open(cs, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            if "-linux-ohos" not in content:
                marker = "\t | -linux* | -uma* | -amigaos* | -amigados* \\"
                if marker in content:
                    content = content.replace(
                        marker, "\t | -linux* | -linux-ohos* | -uma* | -amigaos* | -amigados* \\", 1)
                    with open(cs, "w", encoding="utf-8") as f:
                        f.write(content)

    def build(self):
        if self.settings.os == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "burp2 supports OHOS armv8 (aarch64) only"
            )

        src = self.source_folder.replace("\\", "/")
        shell = os.environ.get("CONFIG_SHELL", "bash")

        # 1) Bootstrap configure — builds aclocal.m4/autom4te cache/configure
        #    from configure.ac + Makefile.am. The upstream tarball does NOT
        #    ship a configure script; reproduce autogen.sh's steps with the
        #    autotools tool_requires. The conan perl tool_require is unusable
        #    on hmfs (Cwd.so dlopen fails), so force the system perl and set
        #    PERL5LIB to the module dir of each tool being invoked:
        #      - aclocal/automake -> share/automake-1.18
        #      - autoconf        -> share/autoconf
        self.run(
            f"{shell} -c \"set -e"
            f" && export PERL=/data/service/hnp/bin/perl"
            f" && cd '{src}'"
            f" && LIBTOOLIZE=$(command -v libtoolize 2>/dev/null || exit 1)"
            f" && unset PERL5LIB"
            f" && sh $LIBTOOLIZE --copy --force"
            f" && ACLOCAL=$(command -v aclocal-1.16 2>/dev/null || command -v aclocal 2>/dev/null || exit 1)"
            f" && unset PERL5LIB"
            f" && export PERL5LIB=$(dirname $(dirname $ACLOCAL))/share/automake-1.18"
            f" && sh $ACLOCAL -I m4"
            f" && AUTOHEADER=$(command -v autoheader 2>/dev/null || exit 1)"
            f" && export PERL5LIB=$(dirname $(dirname $AUTOHEADER))/share/autoconf"
            f" && sh $AUTOHEADER"
            f" && AUTOMAKE=$(command -v automake-1.16 2>/dev/null || command -v automake 2>/dev/null || exit 1)"
            f" && export PERL5LIB=$(dirname $(dirname $AUTOMAKE))/share/automake-1.18"
            f" && sh $AUTOMAKE -a --copy"
            f" && AUTOCONF=$(command -v autoconf 2>/dev/null || exit 1)"
            f" && export PERL5LIB=$(dirname $(dirname $AUTOCONF))/share/autoconf"
            f" && sh $AUTOCONF\"",
            env="conanbuild",
        )
        # 2) Apply recipe patches after bootstrap so the target files exist.
        self._patch_sources()
        # 3) config.guess/config.sub: recognize the OHOS triplet.
        self._patch_config_guess_sub(os.path.join(src, "autoconf"))
        # 4) hmfs: relax umask 077 -> 022 in the generated configure so that
        #    `mktemp -d` inside hmfs creates writable temporary directories.
        self.run(f"{shell} -c "
                 f"\"sed -i 's/umask 077/umask 022/g' '{src}/configure'\"",
                 env="conanbuild")

        # 4) Configure + build. Build CPPFLAGS/LDFLAGS/LIBS from the
        #    requirements so that AC_CHECK_LIB / AC_LINK_IFELSE in
        #    configure.ac can find openssl/zlib/librsync/etc.
        prefix = self.package_folder.replace("\\", "/")
        tmpcache = "/data/storage/el2/base/cache"
        _deps_incs = []
        _deps_libdirs = []
        _deps_libs = []
        # NOTE: do NOT link libcheck into burp/vss_strip: the Makefile.am
        # only links check into the utest `runner` (via CHECK_LIBS), while the
        # packaged burp/vss_strip binaries must stay free of libcheck.so so
        # they run without the test framework at runtime.
        for _dep_name in ("openssl", "zlib", "librsync", "ncurses", "uthash"):
            if _dep_name in self.dependencies:
                _dep = self.dependencies[_dep_name]
                _pf = getattr(_dep, "package_folder", None) or ""
                for _i in _dep.cpp_info.includedirs:
                    _abs = _i if (os.path.isabs(_i) or not _pf) else os.path.join(_pf, _i)
                    if _abs not in _deps_incs:
                        _deps_incs.append(_abs)
                for _l in _dep.cpp_info.libdirs:
                    _abs = _l if (os.path.isabs(_l) or not _pf) else os.path.join(_pf, _l)
                    if _abs not in _deps_libdirs:
                        _deps_libdirs.append(_abs)
                _deps_libs.extend(_dep.cpp_info.libs)
        # check include dir (so configure can detect it for the runner only)
        if "check" in self.dependencies:
            _dep = self.dependencies["check"]
            _pf = getattr(_dep, "package_folder", None) or ""
            for _i in _dep.cpp_info.includedirs:
                _abs = _i if (os.path.isabs(_i) or not _pf) else os.path.join(_pf, _i)
                if _abs not in _deps_incs:
                    _deps_incs.append(_abs)
        _cppflags = " ".join("-I" + i for i in _deps_incs)
        _ldflags = " ".join("-L" + l for l in _deps_libdirs)
        _libs = " ".join("-l" + l for l in _deps_libs)
        _ldpath = ":".join(_deps_libdirs)
        self.run(
            f"{shell} -c "
            f"\"cd '{src}'"
            f" && export TMPDIR={tmpcache}"
            f" && mkdir -p {tmpcache} 2>/dev/null || true"
            f" && export LD_LIBRARY_PATH='{_ldpath}:$LD_LIBRARY_PATH'"
            f" && CPPFLAGS='{_cppflags} $CPPFLAGS'"
            f" LDFLAGS='{_ldflags} $LDFLAGS'"
            f" LIBS='{_libs}'"
            f" CC=clang CXX=clang++ {shell} ./configure --prefix={prefix}"
            f" || {{ echo '=== CONFIG.LOG (tail) ==='; tail -80 config.log 2>/dev/null; exit 1; }}\"",
            env="conanbuild",
        )
        self.run(
            f"{shell} -c "
            f"\"cd '{src}'"
            f" && unset LD_LIBRARY_PATH"
            f" && export TMPDIR={tmpcache}"
            f" && make -j1\"",
            env="conanbuild",
        )
        # 5) Upstream unit tests (Check framework): running make check builds
        #    the `runner` binary and executes the utest suite. Record results.
        #    The runner links -lcheck from the requirements, so expose the
        #    dependency lib dirs via LD_LIBRARY_PATH at runtime. Check's
        #    open_tmp_file picks the temp dir in order TEMP -> P_tmpdir ->
        #    TMPDIR -> ".", and P_tmpdir (/tmp) is read-only on OHOS, so set
        #    TEMP to a writable cache dir (it has the highest precedence).
        self.run(
            f"{shell} -c "
            f"\"cd '{src}'"
            f" && export TEMP={tmpcache} TMPDIR={tmpcache}"
            f" && export LD_LIBRARY_PATH='{_ldpath}:$LD_LIBRARY_PATH'"
            f" && make check 2>&1 | tee upstream-tests.log"
            f" || {{ echo '=== make check failed (exit $?) ==='; tail -60 test-suite.log 2>/dev/null; exit 1; }}\"",
            env="conanbuild",
        )

    def package(self):
        import shutil as _shutil
        src = self.source_folder.replace("\\", "/")
        # `make` (not `make install`) leaves the built binaries at the build
        # dir root: burp (sbin), vss_strip (bin) and the burp_ca script (sbin).
        # Copy them into the package under the conventional locations.
        placements = {
            "burp": "sbin/burp",
            "vss_strip": "bin/vss_strip",
            "burp_ca": "sbin/burp_ca",
        }
        for _rel, _dstrel in placements.items():
            f = os.path.join(src, _rel)
            if os.path.isfile(f):
                dst = os.path.join(self.package_folder, _dstrel)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                _shutil.copy(f, dst)
                _shutil.copymode(f, dst)
                os.chmod(dst, 0o755)
        copy(self, "LICENSE*", src=src,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        for sub in ("bin", "sbin"):
            d = os.path.join(self.package_folder, sub)
            if os.path.isdir(d):
                self.runenv_info.prepend_path("PATH", d)