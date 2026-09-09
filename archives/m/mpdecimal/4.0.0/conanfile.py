#!/usr/bin/env python3
"""Conan recipe for mpdecimal 4.0.0 (autotools, HarmonyOS PC arm64).

mpdecimal is a C/C++ library implementing decimal floating point
arithmetic (General Decimal Arithmetic Specification, IEEE 754-2008).
Pure C/C++ with no third-party dependencies (only system libm).

Adaptations:
- config.guess/config.sub patches recognize aarch64-unknown-linux-ohos.
- Known OHOS dev-host limitation (same as acpid 2.0.34): hmdfs FUSE
  cannot handle autotools' config.status temp dirs (umask 077 quirk),
  so the build is redirected to tmpfs (/data/storage/el2/base).
- Signing wrapper is generated self-contained inside the tmpfs build
  dir (never references a host-specific HOME/tmp/wrapper-bin path):
  conftest/test executables and shared libs need a valid .codesign
  section on OHOS (E135) so the dynamic loader resolves symbols.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class MpdecimalConan(ConanFile):
    name = "mpdecimal"
    version = "4.0.0"
    description = "mpdecimal is a C/C++ library for decimal floating point arithmetic, implementing the General Decimal Arithmetic Specification (IEEE 754-2008)."
    license = "BSD-2-Clause"
    homepage = "https://www.bytereef.org/mpdecimal/"
    url = "https://www.bytereef.org/mpdecimal/"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _build_root(self):
        """Build on tmpfs — hmdfs cannot handle config.status umask 077 dirs."""
        root = "/data/storage/el2/base/.conan-build-mpdecimal-4.0.0"
        return os.path.join(root, "src"), os.path.join(root, "install")

    def _compiler_executables(self):
        """Resolve CC/CXX from Conan conf (profile ohos-aarch64), with fallback."""
        conf = self.conf.get("tools.build:compiler_executables", default={}) or {}
        cc = conf.get("c") or "/data/service/hnp/bin/clang"
        cxx = conf.get("cpp") or "/data/service/hnp/bin/clang++"
        return cc, cxx

    def _generate_wrapper(self, work, name, real_compiler, signer, objcopy):
        """Write a self-contained signing wrapper inside the tmpfs build dir.

        OHOS requires a valid .codesign section on executables and shared
        libs (E135); conftest cannot run otherwise. The wrapper is created
        here (not referenced from $HOME) so it exists in any clean CI
        worker as well. When the signing tools are absent, the wrapper
        transparently delegates to the real compiler.
        """
        wrapper_dir = os.path.join(os.path.dirname(work), "wrapper-bin")
        os.makedirs(wrapper_dir, exist_ok=True)
        wrapper = os.path.join(wrapper_dir, name)
        script = f'''#!/bin/sh
REAL="{real_compiler}"
SIGNER="{signer}"
OBJCOPY="{objcopy}"
OUT=""
prev=""
for arg in "$@"; do
  if [ "$prev" = "-o" ]; then OUT="$arg"; fi
  prev="$arg"
done
"$REAL" "$@"
rc=$?
if [ $rc -eq 0 ] && [ -n "$OUT" ] && [ -f "$OUT" ]; then
  magic=$(head -c4 "$OUT" 2>/dev/null | od -An -tx1 | tr -d ' \\n')
  if [ "$magic" = "7f454c46" ]; then
    if [ -x "$OBJCOPY" ] && [ -x "$SIGNER" ]; then
      "$OBJCOPY" --remove-section .codesign "$OUT" 2>/dev/null
      TMPOUT="$OUT.signed.$$"
      "$SIGNER" sign -selfSign 1 -inFile "$OUT" -outFile "$TMPOUT" -signAlg SHA256withECDSA >/dev/null 2>&1 && mv -f "$TMPOUT" "$OUT" && chmod 755 "$OUT" 2>/dev/null
      rm -f "$TMPOUT"
    fi
  fi
fi
exit $rc
'''
        with open(wrapper, "w", encoding="utf-8") as f:
            f.write(script)
        os.chmod(wrapper, 0o755)
        return wrapper

    def build(self):
        apply_conandata_patches(self)
        work, install_dir = self._build_root()

        if os.path.isdir(work):
            shutil.rmtree(work, ignore_errors=True)
        os.makedirs(work, exist_ok=True)
        os.makedirs(install_dir, exist_ok=True)
        self.run(f'cp -a "{self.source_folder}/." "{work}/"')

        tmpdir = os.path.join(os.path.dirname(work), "build-tmp")
        os.makedirs(tmpdir, exist_ok=True)

        cc, cxx = self._compiler_executables()
        signer = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        home = os.path.expanduser("~")
        wrapper_cc = self._generate_wrapper(work, "clang", cc, signer, objcopy)
        wrapper_cxx = self._generate_wrapper(work, "clang++", cxx, signer, objcopy)
        if os.path.isdir("/data/service/hnp/binutils.org/binutils_2.45/bin"):
            gnu_ld = "/data/service/hnp/binutils.org/binutils_2.45/bin/ld"
        else:
            gnu_ld = ""  # linker flag resolver below falls back to default ld

        configure_opts = ["--enable-static", "--disable-shared"] if not self.options.shared \
            else ["--enable-shared", "--disable-static"]

        ldflags = f"-fuse-ld={gnu_ld}" if gnu_ld else ""
        env = (
            f"PATH=/data/service/hnp/bin:{home}/usr/local/bin:{os.environ.get('PATH', '')}"
            f" TMPDIR={tmpdir} CONFIG_SHELL=/data/service/hnp/bin/bash"
            f" CC={wrapper_cc} CXX={wrapper_cxx}"
            f" LDFLAGS={ldflags}"
        )

        # Upstream tests need testdata: the tarball does not ship it, so
        # fetch the official decTest archive on demand and extract it.
        self.run(f'bash -c \'cd {work}/tests'
                 f' && if [ ! -f dectest.zip ] && [ ! -d testdata ]; then'
                 f'   curl -fsSL -o dectest.zip http://speleotrove.com/decimal/dectest.zip || true;'
                 f' fi'
                 f' && mkdir -p testdata && if [ -f dectest.zip ]; then'
                 f'   (cd testdata && unzip -qq -o ../dectest.zip) || true;'
                 f' fi\'', ignore_errors=True)

        cfg = " ".join(configure_opts)
        self.run(f'bash -c \'cd {work} && export {env}'
                 f' && ./configure --prefix={install_dir} --disable-doc --disable-pc {cfg}\'')

        jobs = os.cpu_count() or 1
        self.run(f'bash -c \'cd {work} && export {env} && make -j{jobs}\'')
        self.run(f'bash -c \'cd {work} && export {env} && make check\'')
        self.run(f'bash -c \'cd {work} && export {env} && make install\'')

        self._store = (work, install_dir)

    def package(self):
        store = getattr(self, "_store", None)
        if store is None:
            return
        _work, install_dir = store
        for sub in ("include", "lib"):
            src = os.path.join(install_dir, sub)
            if os.path.isdir(src):
                dst = os.path.join(self.package_folder, sub)
                shutil.copytree(src, dst, dirs_exist_ok=True)

    def package_info(self):
        # C library libmpdec (installed as libmpdec.a)
        self.cpp_info.components["mpdecimal"].libs = ["mpdec"]
        self.cpp_info.components["mpdecimal"].set_property("pkg_config_name", "libmpdec")
        # C++ wrapper library libmpdec++ (installed as libmpdec++.a, depends on libmpdec)
        self.cpp_info.components["mpdecpp"].libs = ["mpdec++"]
        self.cpp_info.components["mpdecpp"].requires = ["mpdecimal"]
        self.cpp_info.components["mpdecpp"].set_property("pkg_config_name", "libmpdec++")