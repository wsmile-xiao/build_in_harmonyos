#!/usr/bin/env python3
"""Conan recipe for zh-autoconvert 0.3.16 (library: libhz).

zh-autoconvert (upstream project name **libhz**) is a Chinese HZ/GB/Big5
encoding auto-converter. The build is a plain Makefile project: the
`hzconvert/` directory compiles `libhz.a` and `libhz.so.0.0` (SONAME
`libhz.so.0`, set directly by the Makefile via `-Wl,-soname`).

Adaptation notes for OHOS / Conan:
  * The upstream `hzconvert/Makefile` hardcodes `gcc` for the shared-link step
    and `ar` for the static archive, and links `-ldl` (unused). OHOS ships no
    gcc and no `libdl`, so patch 0001 rewrites those to `$(CC)` / `$(AR)` and
    drops `-ldl`. The compiler/ar/ranlib are taken from the Conan toolchain
    (never from shell env — R33).
  * Build output is redirected to a log file and echoed on failure, because the
    Conan worker's piped output can silently swallow compiler diagnostics.
  * The shared-library SONAME/linker-name files are shipped as real copies of
    the `.0.0` payload (not filesystem symlinks) to avoid HMDFS symlink
    Permission-denied during `package()`.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class ZhAutoconvertConan(ConanFile):
    name = "zh-autoconvert"
    version = "0.3.16"
    description = "Chinese HZ/GB/Big5 encoding auto-converter library (libhz)."
    license = "GPL-2.0-or-later"
    homepage = "https://packages.debian.org/source/zh-autoconvert"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.name}/{self.version} only supports Linux / OHOS, "
                f"got settings.os={self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _run_logged(self, cmd, cwd, logname):
        log = os.path.join(cwd, logname)
        try:
            self.run(f"{cmd} > '{log}' 2>&1", cwd=cwd)
        except Exception:
            self.output.error(f"=== {logname} (tail) ===")
            try:
                with open(log, encoding="utf-8", errors="replace") as fh:
                    for line in fh.readlines()[-60:]:
                        self.output.error(line.rstrip())
            except OSError:
                pass
            raise

    def build(self):
        apply_conandata_patches(self)

        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c") or "clang"
        ar = compilers.get("ar") or "llvm-ar"
        ranlib = compilers.get("ranlib") or "llvm-ranlib"

        hzc = os.path.join(self.source_folder, "hzconvert")
        # hzconvert/Makefile builds both libhz.a and libhz.so.0.0 in one target.
        # -fsigned-char is added defensively (aarch64 defaults char to unsigned;
        # the upstream sources were written for x86 signed char). The table
        # lookups already cast to unsigned char, so this only protects any
        # non-cast code path.
        self._run_logged(
            f"make CC='{cc} -I../include' CFLAGS='-O2 -Wall -g -fsigned-char' "
            f"AR={ar} RANLIB={ranlib} -j1",
            hzc,
            "build.log",
        )

    def _materialize_lib_symlinks(self):
        # OHOS / HMDFS: a SONAME-name symlink under lib/ cannot be loaded at
        # runtime (DT_NEEDED resolution hits EACCES). Convert any symlink in the
        # packaged lib/ into a real copy of its target.
        libdir = os.path.join(self.package_folder, "lib")
        if not os.path.isdir(libdir):
            return
        for entry in os.listdir(libdir):
            p = os.path.join(libdir, entry)
            if os.path.islink(p):
                target = os.path.realpath(p)
                os.remove(p)
                shutil.copy2(target, p)

    def package(self):
        # Public headers live in the upstream `include/` directory. Copy from
        # that directory (not recursively from source root) so they land at
        # package/include/hz.h instead of package/include/include/hz.h.
        include_src = os.path.join(self.source_folder, "include")
        copy(
            self,
            "*.h",
            include_src,
            os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            "libhz.a",
            os.path.join(self.source_folder, "lib"),
            os.path.join(self.package_folder, "lib"),
        )
        if self.options.shared:
            libdir = os.path.join(self.package_folder, "lib")
            copy(self, "libhz.so.0.0", os.path.join(self.source_folder, "lib"), libdir)
            # Ship SONAME/linker-name files as real copies (no symlinks — HMDFS
            # symlink Permission-denied). The ELF itself carries DT_SONAME
            # libhz.so.0, so the runtime loader resolves it correctly.
            shutil.copy2(
                os.path.join(libdir, "libhz.so.0.0"),
                os.path.join(libdir, "libhz.so.0"),
            )
            shutil.copy2(
                os.path.join(libdir, "libhz.so.0"),
                os.path.join(libdir, "libhz.so"),
            )
        self._materialize_lib_symlinks()
        self._sign_binaries()

    def _sign_binaries(self):
        # OHOS refuses to load/exec unsigned ELF binaries, so the shipped
        # shared library must carry a codesign section. The Makefile/toolchain
        # may have left a stale .codesign section behind — strip it first, then
        # re-sign. The profile's [buildenv] prepends the SDK llvm/lib to
        # LD_LIBRARY_PATH, which shadows the sign tool's system libc++, so the
        # sign call runs with LD_LIBRARY_PATH unset (per E316/E492).
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if self.settings.os != "OHOS" or not os.path.exists(sign_tool):
            return
        libdir = os.path.join(self.package_folder, "lib")
        if not os.path.isdir(libdir):
            return
        for entry in sorted(os.listdir(libdir)):
            if ".so" not in entry:
                continue
            p = os.path.join(libdir, entry)
            if os.path.islink(p):
                continue
            tmp = p + ".signed"
            self.run(
                f"{objcopy} --remove-section .codesign {p} 2>/dev/null || true",
                env="conanbuild",
            )
            self.run(
                f"env -u LD_LIBRARY_PATH {sign_tool} sign -inFile {p} "
                f"-outFile {tmp} -selfSign 1",
                env="conanbuild",
            )
            os.replace(tmp, p)
            os.chmod(p, 0o755)

    def package_info(self):
        self.cpp_info.libs = ["hz"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
