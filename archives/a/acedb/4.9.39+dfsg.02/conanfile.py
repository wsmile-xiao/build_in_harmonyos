#!/usr/bin/env python3
"""Conan recipe for acedb 4.9.39+dfsg.02 using the custom wmake system."""

import hashlib
import glob
import os
import re
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, chmod, export_conandata_patches, get
from conan.tools.layout import basic_layout


def _get_prefix():
    return os.environ.get("DEFAULT_PREFIX", os.path.expanduser("~/usr/local"))


def _cmd_pkg_ready(prefix, expected_paths):
    return all((Path(prefix) / relative_path).exists() for relative_path in expected_paths)


# GLib static archives reference the g_libintl_* aliases that the gettext
# proxy libintl normally exports. cmd-pkgs' libintl.a only exports libintl_*,
# so provide a small proxy library mirroring the gettext aliases.
GINTL_C = r"""
#include <stddef.h>

extern char *libintl_bindtextdomain(const char *, const char *);
extern char *libintl_bind_textdomain_codeset(const char *, const char *);
extern char *libintl_dcgettext(const char *, const char *, int);
extern char *libintl_dgettext(const char *, const char *);
extern char *libintl_dngettext(const char *, const char *, const char *, unsigned long);
extern char *libintl_gettext(const char *);
extern char *libintl_ngettext(const char *, const char *, unsigned long);
extern char *libintl_textdomain(const char *);

char *g_libintl_bindtextdomain(const char *d, const char *dir) { return libintl_bindtextdomain(d, dir); }
char *g_libintl_bind_textdomain_codeset(const char *d, const char *c) { return libintl_bind_textdomain_codeset(d, c); }
char *g_libintl_dcgettext(const char *d, const char *m, int cat) { return libintl_dcgettext(d, m, cat); }
char *g_libintl_dgettext(const char *d, const char *m) { return libintl_dgettext(d, m); }
char *g_libintl_dngettext(const char *d, const char *m, const char *p, unsigned long n) { return libintl_dngettext(d, m, p, n); }
char *g_libintl_gettext(const char *m) { return libintl_gettext(m); }
char *g_libintl_ngettext(const char *m, const char *p, unsigned long n) { return libintl_ngettext(m, p, n); }
char *g_libintl_textdomain(const char *d) { return libintl_textdomain(d); }
"""



def _install_cmd_pkg(name, version, sha256, prefix):
    url = (
        "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/"
        f"pkgs/{name}-{version}-ohos-aarch64.tar.gz"
    )
    os.makedirs(prefix, exist_ok=True)
    archive = os.path.join(prefix, f".install-{name}-{version}.tar.gz")
    try:
        urllib.request.urlretrieve(url, archive)
        digest = hashlib.sha256(Path(archive).read_bytes()).hexdigest()
        if digest != sha256:
            raise ConanInvalidConfiguration(f"cmd-pkgs checksum mismatch: {name}/{version}")
        with tempfile.TemporaryDirectory(prefix=f"acedb-{name}-") as staging:
            with tarfile.open(archive, "r:gz") as package:
                destination = Path(prefix).resolve()
                for member in package.getmembers():
                    target = (destination / member.name).resolve()
                    if destination not in target.parents and target != destination:
                        raise ConanInvalidConfiguration(f"unsafe cmd-pkgs archive entry: {member.name}")
                    if member.issym():
                        link_target = (Path(staging) / member.name).parent / member.linkname
                        if Path(staging).resolve() not in link_target.resolve().parents:
                            raise ConanInvalidConfiguration(f"unsafe cmd-pkgs symlink: {member.name}")
                    elif not (member.isdir() or member.isreg()):
                        raise ConanInvalidConfiguration(f"unsupported cmd-pkgs archive entry: {member.name}")
                package.extractall(staging)
            staged_root = Path(staging).resolve()
            for staged in staged_root.rglob("*"):
                if staged.is_symlink():
                    if staged_root not in staged.resolve().parents:
                        raise ConanInvalidConfiguration(f"unsafe extracted cmd-pkgs symlink: {staged}")
                elif not (staged.is_file() or staged.is_dir()):
                    raise ConanInvalidConfiguration(f"unsafe extracted cmd-pkgs entry: {staged}")
                relative = staged.relative_to(staged_root)
                target = destination / relative
                if staged.is_dir():
                    if target.exists() and target.is_symlink():
                        raise ConanInvalidConfiguration(f"existing cmd-pkgs directory symlink: {relative}")
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                resolved_parent = target.parent.resolve()
                if destination not in resolved_parent.parents and resolved_parent != destination:
                    raise ConanInvalidConfiguration(f"cmd-pkgs target escapes prefix: {relative}")
                if target.exists() and target.is_symlink():
                    raise ConanInvalidConfiguration(f"existing cmd-pkgs file symlink: {relative}")
                shutil.copy2(staged, target)
    finally:
        if os.path.exists(archive):
            os.remove(archive)


class AcedbConan(ConanFile):
    name = "acedb"
    version = "4.9.39+dfsg.02"
    description = "ACeDB genome database system"
    license = "GPL-2.0"
    homepage = "https://github.com/richarddurbin/acedb"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "compiler", "build_type", "arch"
    package_type = "application"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("glib/2.88.0")
        self.requires("gettext/0.22.5")
        self.requires("ncurses/6.6")
        self.requires("readline/8.3")

    def validate(self):
        if self.settings.os != "OHOS":
            raise ConanInvalidConfiguration("this recipe is an OpenHarmony OHOS adaptation")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        prefix = os.path.join(self.build_folder, "cmd-pkgs")
        os.makedirs(prefix, exist_ok=True)
        packages = (
            ("pcre2", "10.40", "ae90e5fe81e36665e14f4526aa016370a3c667aa1ad477a63b184e67bef99c30", ("lib/libpcre2-8.a",)),
            ("glib", "2.88.0", "ba150ce21fca70c896748f63b432a8f4959e8e20a4f197336debc6f2b967628c", ("include/glib-2.0/glib.h", "lib/libglib-2.0.a", "lib/pkgconfig/glib-2.0.pc")),
            ("gettext", "0.22.5", "d1786139856aad8db349c7289d3e093ab2f854ee4f4d3ea5012a275babe2a502", ("include/libintl.h", "lib/libintl.a")),
            ("readline", "8.2", "d5f4c0b99f12f1562b62dc0af30ca5badc3c37f4ad7670a63ab5f46aa66751ed", ("include/readline/readline.h", "lib/libreadline.a")),
            ("ncurses", "6.4", "e746bbe540e68c216493a00430e9047cc83f3d98f66fbe65f9e4cf1c8eb6cde8", ("lib/libncursesw.a",)),
        )
        for name, version, sha256, expected_paths in packages:
            _install_cmd_pkg(name, version, sha256, prefix)
            if not _cmd_pkg_ready(prefix, expected_paths):
                raise ConanInvalidConfiguration(f"cmd-pkgs dependency is incomplete: {name}/{version}")

        flex = shutil.which("flex")
        if not flex:
            raise ConanInvalidConfiguration("OpenHarmony toolchain flex 2.6.4 is required")
        flex_version = subprocess.run([flex, "--version"], capture_output=True, text=True, check=True).stdout
        if "2.6.4" not in flex_version:
            raise ConanInvalidConfiguration("OpenHarmony toolchain flex 2.6.4 is required")
        flex_library = "/data/service/hnp/flex.org/flex_2.6.4/lib/libfl.a"
        flex_library_sha256 = "fcb53f3eccfd7d95c1162eae68e71839e2b02e379aa78e4d32f0b3b4ee24d129"
        if not os.path.exists(flex_library):
            raise ConanInvalidConfiguration("OpenHarmony flex 2.6.4 libfl.a is required")
        if hashlib.sha256(Path(flex_library).read_bytes()).hexdigest() != flex_library_sha256:
            raise ConanInvalidConfiguration("OpenHarmony flex 2.6.4 libfl.a checksum mismatch")

        libdir = os.path.join(prefix, "lib")
        shutil.copy2(flex_library, os.path.join(libdir, "libfl.a"))
        if hashlib.sha256(Path(os.path.join(libdir, "libfl.a")).read_bytes()).hexdigest() != flex_library_sha256:
            raise ConanInvalidConfiguration("controlled prefix libfl.a checksum mismatch")
        pkgconfig = os.path.join(libdir, "pkgconfig")
        for pc_file in glob.glob(os.path.join(pkgconfig, "*.pc")):
            with open(pc_file, encoding="utf-8") as pc_handle:
                pc_content = pc_handle.read()
            pc_content = re.sub(
                r"(?m)^prefix=.*$", f"prefix={prefix}", pc_content
            )
            with open(pc_file, "w", encoding="utf-8") as pc_handle:
                pc_handle.write(pc_content)
        os.environ["PKG_CONFIG_PATH"] = pkgconfig + os.pathsep + os.environ.get("PKG_CONFIG_PATH", "")
        os.environ["LD_LIBRARY_PATH"] = libdir + os.pathsep + os.environ.get("LD_LIBRARY_PATH", "")

        gintl_src = os.path.join(libdir, "gintl.c")
        with open(gintl_src, "w", encoding="utf-8") as gintl_handle:
            gintl_handle.write(GINTL_C)
        gintl_obj = os.path.join(libdir, "gintl.o")
        cc = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ).get("c") or "clang"
        subprocess.run([cc, "-c", gintl_src, "-o", gintl_obj], check=True)
        ar_tool = next(
            (
                candidate
                for candidate in (shutil.which("ar"), shutil.which("llvm-ar"), "/data/service/hnp/bin/ar")
                if candidate and os.path.exists(candidate)
            ),
            None,
        )
        if not ar_tool:
            raise ConanInvalidConfiguration("ar/llvm-ar tool is required")
        subprocess.run([ar_tool, "cru", os.path.join(libdir, "libgintl.a"), gintl_obj], check=True)

        curses = os.path.join(libdir, "libcurses.a")
        if not os.path.exists(curses) and os.path.exists(os.path.join(libdir, "libncursesw.a")):
            os.symlink("libncursesw.a", curses)

        include_dirs = []
        for dependency in ("glib", "gettext", "ncurses", "readline"):
            for include_dir in self.dependencies[dependency].cpp_info.includedirs:
                if include_dir not in include_dirs:
                    include_dirs.append(include_dir)
        include_flags = " ".join(f"-I{include_dir}" for include_dir in include_dirs)
        library_flags = f"-L{libdir}"
        def_path = os.path.join(self.source_folder, "wmake", "OHOS_4_DEF")
        os.makedirs(os.path.dirname(def_path), exist_ok=True)
        with open(def_path, "w", encoding="utf-8") as definition:
            definition.write(
                "NAME = LINUX\n\n"
                f"LIBCC = clang\nCOPT = -g -O2 {include_flags}\nLOPT = -g {library_flags}\n\n"
                "GLIB_VER = glib-2.0\n"
                "GLIB_LIBS = `pkg-config --libs glib-2.0` -Wl,-Bstatic "
                "-Wl,--start-group -lintl -lgintl -Wl,--end-group "
                "-Wl,-Bdynamic -lm -lcurses -lreadline\n"
                "LIBS = `pkg-config --libs glib-2.0` -Wl,-Bstatic "
                "-Wl,--start-group -lintl -lgintl -Wl,--end-group "
                "-Wl,-Bdynamic -lm -lcurses -lreadline\n\n"
                "COMPILER = clang $(COPT) -Wall -DLINUX -DACEDB_NO_GTK -DACEDB4 "
                "`pkg-config --cflags glib-2.0`\n"
                "LINKER = clang $(LOPT)\n\n"
                "LEX_LIBS = -lfl\nLEX = flex\nLEX_OPTIONS = -l\n"
                "YACC = yacc\nYACC_OPTIONS =\nRPCGEN_FLAGS = -b -I\n"
                "AR_COMMAND = ar\nAR_OPTIONS = cru\nRANLIB_NEEDED = true\n"
            )

    def build(self):
        os.environ["ACEDB_MACHINE"] = "OHOS_4"
        os.environ.setdefault("SHELL", "/data/service/hnp/bin/bash")
        os.environ.setdefault("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        makefile = os.path.join(self.source_folder, "Makefile")
        if not os.path.exists(makefile):
            os.symlink("wmake/makefile", makefile)
        self.run(
            "make -j1 libfree.a libace.a tace taql acediff acediffsorted "
            "makeUserPasswd tagcount md5test",
            cwd=self.source_folder,
        )

    def package(self):
        source_bin = os.path.join(self.source_folder, "bin.OHOS_4")
        target_bin = os.path.join(self.package_folder, "bin")
        os.makedirs(target_bin, exist_ok=True)
        binaries = [
            "tace", "taql", "acediff", "acediffsorted", "makeUserPasswd",
            "tagcount", "mddriver", "digtest",
        ]
        for binary in binaries:
            source = os.path.join(source_bin, binary)
            if not os.path.exists(source):
                raise ConanInvalidConfiguration(f"expected built executable is missing: {binary}")
            shutil.copy2(source, os.path.join(target_bin, binary))
            chmod(self, os.path.join(target_bin, binary), 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
