import os
import shutil
from pathlib import Path

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class MakepkgConan(ConanFile):
    name = "makepkg"
    version = "6.0.2"
    description = "Arch Linux makepkg packaging script from pacman"
    license = "GPL-2.0-or-later"
    homepage = "https://archlinux.org/pacman/"
    url = ""

    package_type = "application"
    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        generated = Path(self.build_folder) / "generated"
        self._generate_tree(generated)

        bash = self._bash()
        self.run(f'"{bash}" -n "{generated / "bin" / "makepkg"}"')
        for script in (generated / "share" / "makepkg").rglob("*.sh"):
            self.run(f'"{bash}" -n "{script}"')
        self._run_upstream_script_tests(generated)

    def package(self):
        generated = Path(self.build_folder) / "generated"
        if not generated.exists():
            self._generate_tree(generated)

        copy(self, "makepkg", src=generated / "bin", dst=Path(self.package_folder) / "bin")
        copy(self, "*.sh", src=generated / "share" / "makepkg",
             dst=Path(self.package_folder) / "share" / "makepkg")
        copy(self, "*.conf", src=generated / "etc", dst=Path(self.package_folder) / "etc")
        copy(self, "COPYING", src=self.source_folder, dst=Path(self.package_folder) / "licenses")
        (Path(self.package_folder) / "bin" / "makepkg").chmod(0o755)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.define_path(
            "MAKEPKG_CONF",
            os.path.join(self.package_folder, "etc", "makepkg.conf"),
        )

    def _bash(self):
        return os.environ.get("CONAN_BASH") or shutil.which("bash") or "/data/service/hnp/bin/bash"

    def _generate_tree(self, dst_root):
        dst_root = Path(dst_root)
        bin_dir = dst_root / "bin"
        lib_dir = dst_root / "share" / "makepkg"
        etc_dir = dst_root / "etc"
        bin_dir.mkdir(parents=True, exist_ok=True)
        lib_dir.mkdir(parents=True, exist_ok=True)
        etc_dir.mkdir(parents=True, exist_ok=True)

        source_root = Path(self.source_folder)
        substitutions = self._substitutions()

        makepkg = self._render(source_root / "scripts" / "makepkg.sh.in", substitutions)
        makepkg = makepkg.replace(
            "LIBRARY=${LIBRARY:-'/usr/share/makepkg'}",
            'LIBRARY=${LIBRARY:-"$(cd "$(dirname "${BASH_SOURCE[0]}")/../share/makepkg" && pwd -P)"}',
        )
        self._write_executable(bin_dir / "makepkg", makepkg)

        for src in (source_root / "scripts" / "libmakepkg").rglob("*.sh.in"):
            rel = src.relative_to(source_root / "scripts" / "libmakepkg")
            dst = lib_dir / rel.with_suffix("")
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(self._render(src, substitutions), encoding="utf-8", newline="\n")

        conf = self._render(source_root / "etc" / "makepkg.conf.in", substitutions)
        (etc_dir / "makepkg.conf").write_text(conf, encoding="utf-8", newline="\n")

    def _substitutions(self):
        carch = self._carch()
        return {
            "@rootdir@": "/",
            "@localedir@": "/usr/share/locale",
            "@sysconfdir@": "/etc",
            "@localstatedir@": "/var",
            "@libmakepkgdir@": "/usr/share/makepkg",
            "@pkgdatadir@": "/usr/share/pacman",
            "@prefix@": "/usr",
            "@PACKAGE_VERSION@": self.version,
            "@PACKAGE_NAME@": "pacman",
            "@BUILDSCRIPT@": "PKGBUILD",
            "@TEMPLATE_DIR@": "/usr/share/makepkg-template",
            "@DEBUGSUFFIX@": "debug",
            "@INODECMD@": "stat -c '%i %n'",
            "@FILECMD@": "file",
            "@BSDTAR_NO_READ_SPARSE@": "",
            "@CARCH@": carch,
            "@CHOST@": self._chost(carch),
            "@PKGEXT@": ".pkg.tar.gz",
            "@SRCEXT@": ".src.tar.gz",
            "@STRIP_BINARIES@": "--strip-all",
            "@STRIP_SHARED@": "--strip-unneeded",
            "@STRIP_STATIC@": "--strip-debug",
        }

    def _render(self, src, substitutions):
        text = Path(src).read_text(encoding="utf-8")
        for key, value in substitutions.items():
            text = text.replace(key, value)
        if str(self.settings.os) == "OHOS":
            text = text.replace("#!/bin/bash", f"#!{self._bash()}", 1)
        else:
            text = text.replace("#!/bin/bash", "#!/usr/bin/env bash", 1)
        return text

    def _write_executable(self, path, text):
        path.write_text(text, encoding="utf-8", newline="\n")
        path.chmod(0o755)

    def _run_upstream_script_tests(self, generated):
        source_root = Path(self.source_folder)
        bash = self._bash()
        libmakepkg_dir = (Path(generated) / "share" / "makepkg").as_posix() + "/"
        parseopts_test = source_root / "test" / "scripts" / "parseopts_test.sh"
        self.run(
            f'PMTEST_LIBMAKEPKG_DIR="{libmakepkg_dir}" "{bash}" "{parseopts_test}"',
            cwd=source_root,
        )

    def _carch(self):
        arch = str(self.settings.arch)
        return {
            "armv8": "aarch64",
            "x86_64": "x86_64",
        }.get(arch, arch)

    def _chost(self, carch):
        return f"{carch}-unknown-linux-gnu"
