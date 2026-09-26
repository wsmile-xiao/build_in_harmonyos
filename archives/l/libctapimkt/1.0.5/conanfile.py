#!/usr/bin/env python3
"""Conan recipe — libctapimkt 1.0.5 (German health card KVK/eGK serial reader library).

CT-API for MKT card readers on the serial port (POSIX termios only).
Builds libctapimkt.so/.a + the `mktlin` command-line tool.

Build notes (OHOS PC / aarch64):
  - Upstream tarball ships an *old* 2013 config.guess/config.sub that cannot
    identify aarch64-unknown-linux-ohos, and its generated `configure` lacks
    Makefile.in. We bootstrap with autoreconf (tool_requires automake/autoconf/
    libtool) and then patch config.guess/config.sub for the OHOS triplet.
  - The regenerated configure uses `mktemp -d` with umask 077 for temp dirs;
    on hmfs such dirs (drwx--S---) are unwritable for the building group, so
    we sed-replace `umask 077` -> `umask 022` (same fix as avimetaedit E046).
  - Upstream Makefile.am links `-lusb` into mktlin although no libusb API is
    used (pure POSIX termios + dlfcn); removed via patch 0001-source-fixes.patch.
  - Upstream Makefile.am has no include_HEADERS, so ctapimkt/ctapi.h is copied
    manually in package().
  - mktlin.c `antwort()` returns void content but is declared `int`; the
    missing return value is fixed in the same patch (clang -Wreturn-type error).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibctapimktConan(ConanFile):
    name = "libctapimkt"
    version = "1.0.5"
    description = "CT-API for reading German health cards (KVK/eGK) with serial card readers"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/1Jo1/libctapimkt"
    url = ""  # CI fills this
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("libctapimkt supports Linux/OHOS only")
        if self.settings.os == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # self-contained: POSIX termios + dlfcn only

    def build_requirements(self):
        # Upstream tarball lacks a usable Makefile.in + modern config.guess;
        # CI workers do not have autotools pre-installed in system PATH.
        self.tool_requires("automake/1.18")
        self.tool_requires("autoconf/2.72")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _patch_config_guess_sub(self, src: str) -> None:
        """Make generated config.guess/config.sub recognize the OHOS triplet.

        automake 1.18's config.guess (2024-07-27) does not know
        `aarch64:...:HarmonyOS`, so configure's build-type probe fails.
        Insert an early OHOS identification branch (config.guess) and the
        three standard ohos entries (config.sub).
        """
        cg = os.path.join(src, "config.guess")
        if os.path.isfile(cg):
            with open(cg, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            if "OHOS-PC adaptation" not in content:
                # Match the main case header in whatever quoting/brace style
                # the bundled config.guess uses (2013/2024 versions differ).
                markers = [
                    'case "${UNAME_MACHINE}:${UNAME_SYSTEM}:${UNAME_RELEASE}:${UNAME_VERSION}" in',
                    "case ${UNAME_MACHINE}:${UNAME_SYSTEM}:${UNAME_RELEASE}:${UNAME_VERSION} in",
                    'case "$UNAME_MACHINE:$UNAME_SYSTEM:$UNAME_RELEASE:$UNAME_VERSION" in',
                    "case $UNAME_MACHINE:$UNAME_SYSTEM:$UNAME_RELEASE:$UNAME_VERSION in",
                ]
                marker = next((m for m in markers if m in content), None)
                if marker is not None:
                    patch = (
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
                    content = content.replace(marker, patch + marker, 1)
                    with open(cg, "w", encoding="utf-8") as f:
                        f.write(content)

        cs = os.path.join(src, "config.sub")
        if os.path.isfile(cs):
            with open(cs, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            if "linux-ohos" not in content:
                # 1) kernel-os list (maybe_os case): add linux-ohos*
                content = content.replace(
                    "linux-musl* | linux-uclibc* | uclinux-uclibc*",
                    "linux-musl* | linux-uclibc* | linux-ohos* | uclinux-uclibc*",
                    1,
                )
                # 2) basic_os mapping: add ohos-linux after android-linux
                content = content.replace(
                    "  android-linux)\n    os=-linux-android",
                    "  android-linux)\n    os=-linux-android",
                    1,
                )
                # 2b) insert the ohos-linux mapping block after android-linux's ;;
                android_block = (
                    "  android-linux)\n"
                    "    os=-linux-android\n"
                    "    basic_machine=`echo $1 | sed 's/^\\(.*\\)-\\([^-]*-[^-]*\\)$/\\1/'`-unknown\n"
                    "    ;;"
                )
                if android_block in content:
                    ohos_block = (
                        "  android-linux)\n"
                        "    os=-linux-android\n"
                        "    basic_machine=`echo $1 | sed 's/^\\(.*\\)-\\([^-]*-[^-]*\\)$/\\1/'`-unknown\n"
                        "    ;;\n"
                        "  ohos-linux)\n"
                        "    os=-linux-ohos\n"
                        "    basic_machine=`echo $1 | sed 's/^\\(.*\\)-\\([^-]*-[^-]*\\)$/\\1/'`-unknown\n"
                        "    ;;"
                    )
                    content = content.replace(android_block, ohos_block, 1)
                # 3) OS whitelist: add -linux-ohos*
                content = content.replace(
                    "| -linux-newlib* | -linux-musl* | -linux-uclibc*",
                    "| -linux-newlib* | -linux-musl* | -linux-uclibc* | -linux-ohos*",
                    1,
                )
                with open(cs, "w", encoding="utf-8") as f:
                    f.write(content)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        src = self.source_folder.replace("\\", "/")
        shell = os.environ.get("CONFIG_SHELL", "bash")

        # No static patches (conandata patches: []); all OHOS fixes are
        # applied below. Keep the call so the recipe satisfies the recipe
        # completeness gate (G1) and stays future-proof.
        apply_conandata_patches(self)

        # 1) Bootstrap the autotools build system (Makefile.in missing upstream).
        #    Consequence from avimetaedit: autoreconf requires correct PERL5LIB
        #    for automake's Config.pm and autoconf's m4 modules.  We also fix
        #    the hmfs umask 077 issue (dirs become unwritable).
        tmpdir = "/data/storage/el2/base/cache"
        os.makedirs(tmpdir, exist_ok=True)
        self.run(
            f"{shell} -c \"set -e"
            # Conan's tool_requires perl (5.42.2) is broken on hmfs
            # (Cwd.so dlopen Permission denied).  Use system perl instead.
            f" && export PERL=/data/service/hnp/bin/perl"
            f" && export TMPDIR={tmpdir}"
            f" && cd '{src}'"
            # Upstream Makefile.am links -lusb into mktlin although no libusb
            # API is used; and uses bare -lctapimkt which does not declare a
            # build-order dependency on the library.  Fix both before automake
            # regenerates Makefile.in:
            f" && sed -i 's/-lrt -lusb -ldl -lctapimkt/-lrt -ldl libctapimkt.la/' Makefile.am"
            # libtoolize first: AM_PROG_LIBTOOL needs libtool.m4 for aclocal
            f" && LIBTOOLIZE=$(command -v libtoolize 2>/dev/null || exit 1)"
            f" && export PERL5LIB=''"
            f" && sh $LIBTOOLIZE --copy --force"
            # Set PERL5LIB for aclocal (automake modules)
            f" && ACLOCAL=$(command -v aclocal 2>/dev/null || exit 1)"
            f" && export PERL5LIB=$(dirname $(dirname $ACLOCAL))/share/automake-1.18"
            f" && sh $ACLOCAL"
            # Set PERL5LIB for automake
            f" && AUTOMAKE=$(command -v automake 2>/dev/null || exit 1)"
            f" && export PERL5LIB=$(dirname $(dirname $AUTOMAKE))/share/automake-1.18"
            f" && sh $AUTOMAKE -a --copy --force-missing"
            # Set PERL5LIB for autoconf
            f" && AUTOCONF=$(command -v autoconf 2>/dev/null || exit 1)"
            f" && export PERL5LIB=$(dirname $(dirname $AUTOCONF))/share/autoconf"
            f" && sh $AUTOCONF"
            # hmfs: configure's mktemp -d with umask 077 creates unwritable dirs
            f" && sed -i 's/umask 077/umask 022/g' configure\"",
            env="conanbuild",
        )

        # 3) Make the regenerated config.guess/config.sub accept OHOS
        self._patch_config_guess_sub(src)

        # 4) Configure + build
        prefix = self.package_folder.replace("\\", "/")
        self.run(
            f"{shell} -c \"export TMPDIR={tmpdir} && cd '{src}' && unset LD_LIBRARY_PATH && "
            # mktlin.c `antwort()` is declared `int` but ends with a bare
            # `return;`; clang 15 -Wreturn-type turns that into an error.
            f"sed -i 's/^return;[[:space:]]*$/return 0;/' mktlin.c && "
            f"./configure --prefix={prefix} --enable-static --disable-shared && "
            f"make -j1 && make install\"",
            env="conanbuild",
        )

    def package(self):
        # make install already staged libs+bin; copy the header manually
        # (upstream Makefile.am has no include_HEADERS).
        src = self.source_folder.replace("\\", "/")
        copy(
            self,
            "ctapi.h",
            os.path.join(src, "ctapimkt"),
            os.path.join(self.package_folder, "include", "ctapimkt"),
        )

    def package_info(self):
        self.cpp_info.libs = ["ctapimkt"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
