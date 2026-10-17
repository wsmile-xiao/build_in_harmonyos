import os
import re
import glob

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    copy,
    get,
    replace_in_file,
)
from conan.tools.layout import basic_layout


class MawkConan(ConanFile):
    name = "mawk"
    version = "1.3.4-20260302"
    package_type = "application"
    description = "Interpreter for the AWK programming language"
    license = "GPL-2.0-only"
    homepage = "https://invisible-island.net/mawk/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("mawk supports Linux and OHOS")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("mawk supports only OHOS armv8")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _ohos_env_prefix(self):
        if self.settings.os != "OHOS":
            return ""
        tmpdir = os.path.join(self.build_folder, "mawk-tmp")
        os.makedirs(tmpdir, exist_ok=True)
        return f'CC=clang CFLAGS="-DMAWK_OHOS" TMPDIR="{tmpdir}" '

    def _fix_ohos_man_install(self):
        if self.settings.os != "OHOS":
            return
        # OHOS mktemp/install-sh pollution makes man/Makefile's install target
        # unreliable (non-UTF-8 bytes, broken $RANDOM). Disable the man install
        # entirely; package() copies the pre-built man pages by hand.
        man_make = os.path.join(self.source_folder, "man", "Makefile")
        if os.path.isfile(man_make):
            with open(man_make, "rb") as f:
                raw = f.read()
            # Replace the install recipe body with a no-op, preserving the
            # `install:` target so top-level `make install` still descends.
            fixed = re.sub(
                rb"(?ms)^install:.*?^(?:uninstall:|clean:)",
                b"install: $(TARGET_DIR)\n\t@echo \"man install skipped (OHOS)\"\n\nuninstall:",
                raw,
            )
            if fixed != raw:
                with open(man_make, "wb") as f:
                    f.write(fixed)
        # install-sh builds tmpdir=${TMPDIR-/tmp}/ins$RANDOM-$$; OHOS dash leaves
        # $RANDOM empty, so the mkdir test fails with "mawk.1: No such file or
        # directory". Pin the tmpdir to our fixed mawk-tmp.
        install_sh = os.path.join(self.source_folder, "install-sh")
        with open(install_sh, "rb") as sh_obj:
            sh = sh_obj.read()
        tmpdir = os.path.join(self.build_folder, "mawk-tmp")
        os.makedirs(tmpdir, exist_ok=True)
        sh = sh.replace(
            b'tmpdir=${TMPDIR-/tmp}/ins$RANDOM-$$',
            b'tmpdir="' + tmpdir.encode() + b'/ins.$$"',
        )
        with open(install_sh, "wb") as sh_obj:
            sh_obj.write(sh)

    def build(self):
        triplets = ""
        if self.settings.os == "OHOS":
            replace_in_file(
                self,
                os.path.join(self.source_folder, "configure"),
                'tmp=`(umask 077 && mktemp -d -q "$TMPDIR/csXXXXXX") 2>/dev/null` &&',
                'tmp="$TMPDIR/cs-fixed"\nrm -rf "$tmp"\n(umask 077 && mkdir "$tmp") &&',
            )
            replace_in_file(
                self,
                os.path.join(self.source_folder, "print.c"),
                "#if (defined(HAVE_ISINF) && defined(HAVE_ISNAN))",
                "#if (defined(HAVE_ISINF) && defined(HAVE_ISNAN)) || defined(MAWK_OHOS)",
                strict=True,
            )
            replace_in_file(
                self,
                os.path.join(self.source_folder, "print.c"),
                "isinf(p->dval) || isnan(p->dval)",
                "__builtin_isinf(p->dval) || __builtin_isnan(p->dval)",
                strict=True,
            )
            replace_in_file(
                self,
                os.path.join(self.source_folder, "print.c"),
                "isinf(cp->dval) || isnan(cp->dval)",
                "__builtin_isinf(cp->dval) || __builtin_isnan(cp->dval)",
                strict=True,
            )
            replace_in_file(
                self,
                os.path.join(self.source_folder, "execute.c"),
                "#if defined(HAVE_ISNAN)",
                "#if defined(HAVE_ISNAN) || defined(MAWK_OHOS)",
                strict=True,
            )
            replace_in_file(
                self,
                os.path.join(self.source_folder, "execute.c"),
                "isnan(cp->dval) || isnan((cp + 1)->dval)",
                "__builtin_isnan(cp->dval) || __builtin_isnan((cp + 1)->dval)",
                strict=True,
            )
            triplets = " --build=aarch64-unknown-linux-gnu --host=aarch64-linux-ohos"
        env_prefix = self._ohos_env_prefix()
        self.run(
            f'{env_prefix}sh ./configure{triplets} --prefix="{self.package_folder}"',
            cwd=self.source_folder,
        )
        self._fix_ohos_man_install()
        self.run(f"{env_prefix}make -j1", cwd=self.source_folder)
        self.run(f"{env_prefix}make check", cwd=self.source_folder)

    def package(self):
        self.run(f"{self._ohos_env_prefix()}make install", cwd=self.source_folder)
        # OHOS: man/Makefile install is disabled (mktemp pollution). Copy the
        # pre-built man pages by hand so test_package / users still get docs.
        if self.settings.os == "OHOS":
            man_src = os.path.join(self.source_folder, "man")
            man_dst = os.path.join(self.package_folder, "share", "man")
            for man_file in glob.glob(os.path.join(man_src, "*.1")) + glob.glob(os.path.join(man_src, "*.7")):
                section = man_file[-1]
                section_dir = os.path.join(man_dst, "man" + section)
                os.makedirs(section_dir, exist_ok=True)
                copy(self, os.path.basename(man_file), src=man_src, dst=section_dir)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
