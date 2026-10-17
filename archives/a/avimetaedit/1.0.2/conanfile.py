#!/usr/bin/env python3
"""Conan recipe — avimetaedit 1.0.2 (AVI MetaEdit CLI).

AVI-MetaEdit is a CLI tool for editing metadata in AVI files (public domain,
CC0), maintained by MediaArea / US National Archives.

Build notes:
  - The official source tarball does NOT ship a pre-generated configure;
    the bootstrap replicates Project/GNU/CLI/autogen.sh's four steps
    (aclocal -> automake -> autoconf) to generate it.
  - Project/GNU/CLI/Makefile.am builds the single `avimetaedit` executable,
    bundling vendored ZenLib / TinyXml / MD5 sources. Only the system
    pthread library is required at runtime (no third-party Conan deps).
  - The generated configure uses `mktemp -d` with umask 077 for its temp
    dir; on hmfs/OHOS such dirs (drwx--S---) become unwritable for the
    building group, so build() sed-replaces umask 077 -> 022.
  - tool_requires provides automake/autoconf/libtool for the bootstrap;
    CI workers do not have these pre-installed in the system PATH.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.env import VirtualBuildEnv
from conan.tools.layout import basic_layout


class AvimetaeditConan(ConanFile):
    name = "avimetaedit"
    version = "1.0.2"
    description = "AVI-MetaEdit — edit metadata in AVI files"
    license = "CC0-1.0"
    homepage = "https://mediaarea.net/AVIMetaEdit"
    url = ""  # CI fills this
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build_requirements(self):
        # Autotools bootstrap; CI workers do not have these pre-installed
        self.tool_requires("automake/1.18")
        self.tool_requires("autoconf/2.72")
        self.tool_requires("libtool/2.5.4")

    def generate(self):
        VirtualBuildEnv(self).generate()

    def _patch_config_guess(self, cli: str) -> None:
        """Make the generated config.guess recognize OHOS/HarmonyOS.

        automake 1.18 (from tool_requires) ships a config.guess dated
        2024-07-27 which does not know the `aarch64:...:HarmonyOS` triplet,
        so configure's `checking build system type` fails with "unable to
        guess system type".  Insert an early OHOS identification branch.
        """
        cg = os.path.join(cli, "config.guess")
        if not os.path.isfile(cg):
            return
        with open(cg, "r", encoding="utf-8") as f:
            content = f.read()
        if "OHOS-PC adaptation" in content:
            return  # already patched
        marker = "case $UNAME_MACHINE:$UNAME_SYSTEM:$UNAME_RELEASE:$UNAME_VERSION in"
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
        if marker in content:
            content = content.replace(marker, patch + marker, 1)
            with open(cg, "w", encoding="utf-8") as f:
                f.write(content)

    def build(self):
        if self.settings.os == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "avimetaedit supports OHOS armv8 (aarch64) only"
            )

        src = self.source_folder.replace("\\", "/")
        cli = os.path.join(src, "Project", "GNU", "CLI").replace("\\", "/")
        shell = os.environ.get("CONFIG_SHELL", "bash")

        # 1) Bootstrap configure — replicates autogen.sh four steps.
#    tool_requires provides automake/autoconf/libtool in PATH.
#    IMPORTANT: Conan's tool_requires perl (5.42.2) is unusable on hmfs
#    (Cwd.so dlopen fails Permission denied).  autoconf's autom4te wrapper
#    honours the PERL env var, so we force every perl invocation to the
#    system perl (/data/service/hnp/bin/perl, 5.42.0) and set PERL5LIB to
#    the specific module directory for each tool:
#      - aclocal/automake -> share/automake-1.18
#      - autoconf        -> share/autoconf
#    Guard `command -v` with `|| exit 1` to prevent hanging on empty.
        self.run(
            f"{shell} -c \"set -e"
            f" && export PERL=/data/service/hnp/bin/perl"
            f" && cd '{cli}'"
            f" && ACLOCAL=$(command -v aclocal-1.16 2>/dev/null || command -v aclocal 2>/dev/null || exit 1)"
            f" && unset PERL5LIB"
            f" && export PERL5LIB=$(dirname $(dirname $ACLOCAL))/share/automake-1.18"
            f" && sh $ACLOCAL"
            f" && AUTOMAKE=$(command -v automake-1.16 2>/dev/null || command -v automake 2>/dev/null || exit 1)"
            f" && export PERL5LIB=$(dirname $(dirname $AUTOMAKE))/share/automake-1.18"
            f" && sh $AUTOMAKE -a --copy"
            f" && AUTOCONF=$(command -v autoconf 2>/dev/null || exit 1)"
            f" && export PERL5LIB=$(dirname $(dirname $AUTOCONF))/share/autoconf"
            f" && sh $AUTOCONF"
            # hmfs: relax umask 077 -> 022 in the generated configure
            f" && sed -i 's/umask 077/umask 022/g' configure\"",
            env="conanbuild",
        )
        apply_conandata_patches(self)
        # Make config.guess recognize OHOS/HarmonyOS (automake 1.18's
        # bundled config.guess does not know the aarch64-ohos triplet)
        self._patch_config_guess(cli)

        # 2) Configure + build
        # config.guess probes clang by writing a test file into a temp dir
        # created under $TMPDIR.  Conan's build env may point TMPDIR at a
        # read-only location (~/.cache/tmp) or a dir whose hmfs child dirs
        # are unwritable, so configure fails with "dummy.c: Permission
        # denied".  Use the OHOS sandbox cache dir (writable on OHOS PC
        # and CI), which owns the temp creation reliably.
        # LD_LIBRARY_PATH is cleared so that libs injected by the conan
        # tool_requires (libtool etc.) do not interfere with clang when it
        # links the configure probe program.
        prefix = self.package_folder.replace("\\", "/")
        tmpcache = "/data/storage/el2/base/cache"
        self.run(
            f"{shell} -c "
            f"\"cd '{cli}'"
            f" && unset LD_LIBRARY_PATH"
            f" && export TMPDIR={tmpcache}"
            f" && mkdir -p {tmpcache} 2>/dev/null || true"
            f" && CC=clang CXX=clang++ {shell} ./configure --prefix={prefix}"
            f" || {{ echo '=== CONFIG.LOG (tail) ==='; tail -80 config.log 2>/dev/null; exit 1; }}\"",
            env="conanbuild",
        )
        self.run(
            f"{shell} -c "
            f"\"cd '{cli}'"
            f" && unset LD_LIBRARY_PATH"
            f" && export TMPDIR={tmpcache}"
            f" && make -j1\"",
            env="conanbuild",
        )

    def package(self):
        # Copy the built binary directly into package/bin.  Using
        # `make install DESTDIR=...` would nest the path (DESTDIR +
        # --prefix), leaving the binary outside package/bin so the
        # test_package runenv cannot find it.
        import shutil as _shutil
        cli = os.path.join(self.source_folder, "Project", "GNU", "CLI").replace("\\", "/")
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        src_bin = os.path.join(cli, "avimetaedit")
        if not os.path.isfile(src_bin):
            raise ConanInvalidConfiguration(
                f"built binary not found at {src_bin}"
            )
        _shutil.copy(src_bin, os.path.join(bin_dir, "avimetaedit"))
        _shutil.copymode(src_bin, os.path.join(bin_dir, "avimetaedit"))

    def package_info(self):
        # Expose the installed binary to consumers both at build and at
        # run time: buildenv_info for conanbuild, runenv_info so that the
        # test_package's conanrun environment can find `avimetaedit`.
        bin_dir = os.path.join(self.package_folder, "bin")
        self.buildenv_info.define_path("PATH", bin_dir)
        self.runenv_info.prepend_path("PATH", bin_dir)