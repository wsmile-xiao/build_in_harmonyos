#!/usr/bin/env python3
"""Conan recipe for wily 0.13.42 on HarmonyOS PC.

wily is an old Acme-like X11/Xt text editor and window manager built with
Autoconf 2.4.  The upstream release has no automated test suite.  The program
initializes Xt in xtbinit() before it parses wily's own options, so there is no
non-GUI --version or --help path that can be used as a smoke test.

The recipe uses the available Conan X11 packages.  wily directly needs libXt
and libX11; libXmu and libXi are not referenced by this source tree.  A private
staging prefix is assembled from every host dependency so the old configure
script sees a conventional include/ and lib/ layout even though Conan stores
transitive packages in separate package folders.  This also materializes real
files for linker names and SONAMEs, avoiding symlink assumptions on HMFS.
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


_SIGN_TOOL = "/data/service/hnp/bin/binary-sign-tool"
_OBJCOPY = "/data/service/hnp/bin/llvm-objcopy"


class WilyConan(ConanFile):
    name = "wily"
    version = "0.13.42"
    description = "Acme-like X11 text editor and window manager"
    license = "HPND"
    homepage = "https://packages.debian.org/sid/wily"
    url = "https://deb.debian.org/debian/pool/main/w/wily/"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"wily supports Linux and OHOS, not {self.settings.os}"
            )

    def requirements(self):
        # Direct X11 API use: libX11 for Xlib and libXt for the X Toolkit.
        # libxt already carries libsm/libice/xorgproto, while libx11 carries
        # xorgproto/libxcb/libxau/xtrans/xcb-proto.  Pin libx11 explicitly so
        # both direct dependencies resolve to the same ABI track.
        self.requires("libxt/1.3.1", transitive_headers=True, transitive_libs=True)
        self.requires("libx11/1.8.13", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _dependency_dirs(self, attribute):
        result = []
        for dependency in self.dependencies.host.values():
            for entry in getattr(dependency.cpp_info, attribute, None) or []:
                path = entry
                if not os.path.isabs(path):
                    path = os.path.join(dependency.package_folder, path)
                if os.path.isdir(path) and path not in result:
                    result.append(path)
        return result

    def _build_stage(self):
        """Assemble one old-style X11 prefix from the Conan dependency graph."""
        stage = os.path.join(self.build_folder, "x11stage")
        if os.path.isdir(stage):
            shutil.rmtree(stage)
        include_dir = os.path.join(stage, "include")
        lib_dir = os.path.join(stage, "lib")
        os.makedirs(include_dir, exist_ok=True)
        os.makedirs(lib_dir, exist_ok=True)

        for source in self._dependency_dirs("includedirs"):
            shutil.copytree(source, include_dir, dirs_exist_ok=True)

        copied = set()
        for source in self._dependency_dirs("libdirs"):
            for name in sorted(os.listdir(source)):
                if name in copied or not (name.endswith(".so") or ".so." in name
                                          or name.endswith(".a")):
                    continue
                entry = os.path.join(source, name)
                real = os.path.realpath(entry)
                if not os.path.isfile(real):
                    continue
                shutil.copy2(real, os.path.join(lib_dir, name))
                copied.add(name)

        # Materialize the unversioned linker name even when the dependency
        # package's symlink was not preserved on HMFS.
        for name in tuple(copied):
            if ".so." not in name:
                continue
            linker_name = name.split(".so.", 1)[0] + ".so"
            if linker_name in copied:
                continue
            shutil.copy2(
                os.path.join(lib_dir, name),
                os.path.join(lib_dir, linker_name),
            )
            copied.add(linker_name)

        if not os.path.isfile(os.path.join(include_dir, "X11", "Intrinsic.h")):
            raise ConanException("staged X11 headers are missing X11/Intrinsic.h")
        for library in ("libXt.so", "libX11.so"):
            if not os.path.isfile(os.path.join(lib_dir, library)):
                raise ConanException(f"staged X11 libraries are missing {library}")
        return stage

    def generate(self):
        stage = self._build_stage()
        stage_include = os.path.join(stage, "include")
        stage_lib = os.path.join(stage, "lib")

        tc = AutotoolsToolchain(self)
        # This Autoconf 2.4 tree predates the directory options emitted by
        # modern AutotoolsToolchain. Keep --prefix and prune the rest.
        tc.update_configure_args({
            "--bindir": None,
            "--sbindir": None,
            "--libdir": None,
            "--includedir": None,
            "--oldincludedir": None,
            "--datarootdir": None,
        })
        tc.configure_args.extend(
            [
                "--with-x",
                f"--x-includes={stage_include}",
                f"--x-libraries={stage_lib}",
            ]
        )
        if str(self.settings.os) == "OHOS":
            # config.guess in this 1990s tree cannot recognize HarmonyOS.
            tc.configure_args.extend(
                [
                    "--build=aarch64-unknown-linux-gnu",
                    "--host=aarch64-unknown-linux-gnu",
                ]
            )

        # The Makefiles consume @X_CFLAGS@ and @X_LIBS@ rather than CPPFLAGS.
        # -std=gnu89 and -fcommon preserve the compilation model expected by
        # this pre-C99 source (implicit function declarations and tentative
        # definitions).
        tc.extra_cflags.extend(["-std=gnu89", "-fcommon"])
        tc.extra_ldflags.append(f"-L{stage_lib}")

        temporary = os.path.join(self.build_folder, "tmp")
        os.makedirs(temporary, exist_ok=True)
        environment = tc.environment()
        environment.define_path("TMPDIR", temporary)
        environment.define("X_CFLAGS", f"-I{stage_include}")
        environment.define("X_LIBS", f"-L{stage_lib}")
        tc.generate(env=environment)

    def _prepend_toolchain_path(self):
        """Make clang's ld.lld/as/nm helpers visible on restricted OHOS PATHs."""
        c_compiler = None
        try:
            compilers = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            )
            c_compiler = compilers.get("c") or compilers.get("cpp")
        except Exception:
            c_compiler = None
        if not c_compiler:
            c_compiler = os.environ.get("CC")
        if not c_compiler:
            return
        toolchain_dir = os.path.dirname(c_compiler)
        if not toolchain_dir:
            return
        current = os.environ.get("PATH", "")
        entries = current.split(os.pathsep) if current else []
        if toolchain_dir not in entries:
            os.environ["PATH"] = toolchain_dir + os.pathsep + current

    def _restore_script_modes(self):
        for name in ("configure", "config.guess", "config.sub", "install-sh"):
            path = os.path.join(self.source_folder, name)
            if not os.path.isfile(path):
                continue
            try:
                os.chmod(path, os.stat(path).st_mode | 0o111)
            except OSError:
                pass

    def _patch_configure(self):
        configure = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(configure):
            raise ConanException(f"upstream configure script is missing: {configure}")
        with open(configure, "r", encoding="utf-8", errors="ignore") as handle:
            text = handle.read()
        original = text
        text = text.replace("umask 077", "umask 022")
        if "if (pwd) >/dev/null 2>&1; then :; else" in text:
            text = text.replace(
                "if (pwd) >/dev/null 2>&1; then :; else",
                'if (pwd) >/dev/null 2>&1 || test -n "$PWD"; then :; else',
            )
        if text != original:
            with open(configure, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(text)

    def _prepare_build_tree(self):
        self._restore_script_modes()
        self._patch_configure()
        for directory in ("libXg", "libframe", "libmsg", "wily"):
            os.makedirs(os.path.join(self.build_folder, directory), exist_ok=True)

    def build(self):
        apply_conandata_patches(self)
        self._prepend_toolchain_path()
        temporary = os.path.join(self.build_folder, "tmp")
        os.makedirs(temporary, exist_ok=True)
        os.environ["TMPDIR"] = temporary
        os.environ["TMP"] = temporary
        os.environ["TEMP"] = temporary
        try:
            os.chdir(self.build_folder)
        except OSError:
            pass
        os.environ["PWD"] = self.build_folder
        self._prepare_build_tree()

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # Upstream ships no check/TESTS target.  Do not invent a make check.

    def _is_elf(self, path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_elf(self, path):
        if not self._is_elf(path):
            return
        if os.path.isfile(_SIGN_TOOL):
            self.run(f'{_OBJCOPY} --remove-section .codesign "{path}" 2>/dev/null || true')
            self.run(f'{_SIGN_TOOL} sign -inFile "{path}" -outFile "{path}" -selfSign 1')
        try:
            os.chmod(path, 0o755)
        except OSError:
            pass

    def package(self):
        os.makedirs(os.path.join(self.package_folder, "bin"), exist_ok=True)
        # The generated Autoconf 2.4 Makefile ignores DESTDIR and would
        # install to the configure-time prefix (/bin). Package the binary
        # directly so the Conan package folder remains the only write target.
        built = os.path.join(self.build_folder, "wily", "wily")
        if not os.path.isfile(built):
            raise ConanException(f"wily executable was not produced: {built}")

        binary = os.path.join(self.package_folder, "bin", "wily")
        copy(self, "wily", src=os.path.dirname(built), dst=os.path.dirname(binary))
        copy(
            self,
            "README",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        self._sign_elf(binary)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
