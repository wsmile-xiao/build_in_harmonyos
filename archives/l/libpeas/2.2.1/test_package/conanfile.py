import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.layout import basic_layout


class LibpeasTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "PkgConfigDeps"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build_requirements(self):
        self.tool_requires("pkgconf/3.0.5")

    def layout(self):
        basic_layout(self)

    def build(self):
        # Compile against the libpeas-2.pc / glib-*.pc emitted by PkgConfigDeps
        # (CMakeDeps carries no include dirs for the glib2 component package).
        # The compiler path is pinned absolute (R33: no undefined shell env).
        # Output goes to a local-disk dir: binaries under the repo (HMDFS)
        # cannot be exec'd (E524 — HMDFS ignores chmod/X_OK).
        src = self.source_folder
        conan_home = os.environ.get("CONAN_HOME", os.path.join(os.path.expanduser("~"), ".conan2"))
        out = os.path.join(conan_home, "libpeas6691-testpkg")
        os.makedirs(out, exist_ok=True)
        gen = self.build_folder  # basic_layout: pc files land in <build>/conan
        executables = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        compiler = executables.get("c") or os.environ.get("CC") or shutil.which("clang")
        if not compiler:
            raise ConanInvalidConfiguration("cannot locate the configured C compiler")
        with VirtualBuildEnv(self).vars().apply():
            self.run(
                'cd {src} && PKG_CONFIG_PATH={pcpath} {compiler} test_libpeas.c '
                '-o {binary} $(PKG_CONFIG_PATH={pcpath} pkg-config --cflags --libs '
                'libpeas-2 glib-2.0 gobject-2.0 gio-2.0 gmodule-2.0)'.format(
                    src=shlex.quote(src), pcpath=shlex.quote(os.path.join(gen, "conan")),
                    compiler=shlex.quote(compiler), binary=shlex.quote(os.path.join(out, "test_libpeas")))
            )

    def test(self):
        if not can_run(self):
            self.output.info("Skipping test_libpeas execution: target binaries are not runnable")
            return
        # OHOS: /system/bin/sh (mksh) cannot exec ELF binaries; wrap with bash.
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"
        with VirtualRunEnv(self).vars().apply():
            conan_home = os.environ.get("CONAN_HOME", os.path.join(os.path.expanduser("~"), ".conan2"))
            out = os.path.join(conan_home, "libpeas6691-testpkg")
            libdirs = [self.dependencies["glib"].cpp_info.libdirs[0]]
            # HMDFS ignores chmod (E524): the packaged .so (mode 750) cannot
            # be dlopen'd, while the meson build tree copy (mode 775) can.
            # Glob the actual build tree inside the conan cache (drogon
            # precedent) and prepend it to LD_LIBRARY_PATH. On CI workers
            # can_run() is False and this branch never executes.
            import glob as _glob
            # Conan cache home varies: local runs use ~/.conan2, CI workers
            # use ~/.cache/conan2 (see CI log paths) — search both plus $CONAN_HOME.
            cache_roots = [
                os.path.expanduser("~/.conan2"),
                os.path.expanduser("~/.cache/conan2"),
                os.environ.get("CONAN_HOME", ""),
            ]
            for _root in cache_roots:
                if not _root:
                    continue
                for _d in sorted(_glob.glob(os.path.join(
                        _root, "p", "b", "libpe*", "b", "build-release", "libpeas")),
                        reverse=True):
                    if os.path.exists(os.path.join(_d, "libpeas-2.so.0.200.1")):
                        libdirs.insert(0, _d)
                        break
                else:
                    continue
                break
            self.run('{bash} -c "cd {out} && LD_LIBRARY_PATH={libs} ./test_libpeas"'.format(
                bash=shlex.quote(bash), out=shlex.quote(out), libs=shlex.quote(":".join(libdirs))))
