#!/usr/bin/env python3
"""Consumer test for libsecret 0.20.5 — meson + pkg-config consumer (R34).

The glib package ships pkg-config metadata only (CMakeDeps include dirs come
out empty for it), so the consumer builds with Meson + PkgConfigDeps, matching
the main recipe's proven dependency resolution path.
"""
import os
import re
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LibsecretTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # glib-2.0.pc Requires: proxy-libintl + libpcre2-8; making them direct
        # here lets PkgConfigDeps emit .pc for each (upstream ships none).
        self.requires("proxy-libintl/0.5")
        self.requires("pcre2/10.47")
        self.requires("libffi/3.5.2")
        self.requires("zlib/1.3.2")
        self.requires("libgpg-error/1.55")

    def layout(self):
        basic_layout(self, src_folder=".")

    def generate(self):
        PkgConfigDeps(self).generate()
        # Dependency .pc files ship "prefix=/" — rewrite to the real package
        # folder so pkg-config resolves includes/libs inside the Conan cache.
        for dep in self.dependencies.values():
            if not dep.package_folder:
                continue
            src_pc = os.path.join(dep.package_folder, "lib", "pkgconfig")
            if os.path.isdir(src_pc):
                real_prefix = dep.package_folder.replace(os.sep, "/")
                for pc_name in os.listdir(src_pc):
                    if not pc_name.endswith(".pc"):
                        continue
                    with open(os.path.join(src_pc, pc_name), encoding="utf-8") as handle:
                        content = handle.read()
                    rewritten = re.sub(
                        r"^prefix=.*$", "prefix={}".format(real_prefix),
                        content, flags=re.MULTILINE,
                    )
                    with open(
                        os.path.join(self.generators_folder, pc_name),
                        "w", encoding="utf-8", newline="\n",
                    ) as handle:
                        handle.write(rewritten)
        # proxy-libintl has no .pc but glib-2.0.pc Requires it. It is a
        # transitive dep here, so locate it by its libintl.h artifact.
        for dep in self.dependencies.values():
            if dep.package_folder and os.path.isfile(
                os.path.join(dep.package_folder, "include", "libintl.h")
            ):
                with open(
                    os.path.join(self.generators_folder, "proxy-libintl.pc"),
                    "w", encoding="utf-8", newline="\n",
                ) as handle:
                    handle.write(
                        "prefix={}\n".format(dep.package_folder.replace(os.sep, "/"))
                        + "libdir=${prefix}/lib\nincludedir=${prefix}/include\n\n"
                        + "Name: proxy-libintl\nDescription: intl proxy\nVersion: 0.5\n"
                        + "Libs: -L${libdir} -lintl\nCflags: -I${includedir}\n"
                    )
                break
        # Point meson at the host pkg-config for OHOS cross builds.
        pkg_config = self.conf.get("tools.gnu:pkg_config", default=None)
        if pkg_config and os.path.isfile(str(pkg_config)):
            replacement = "pkg-config = '{}'".format(os.path.abspath(str(pkg_config)))
            for filename in ("conan_meson_native.ini", "conan_meson_cross.ini"):
                machine_file = os.path.join(self.generators_folder, filename)
                if not os.path.isfile(machine_file):
                    continue
                with open(machine_file, encoding="utf-8") as handle:
                    content = handle.read()
                if "pkg-config =" not in content:
                    content = content.replace(
                        "[binaries]\n", "[binaries]\n{}\n".format(replacement), 1
                    )
                    with open(machine_file, "w", encoding="utf-8", newline="\n") as handle:
                        handle.write(content)
        VirtualRunEnv(self).generate()
        MesonToolchain(self).generate()

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()
        meson.install()

    def test(self):
        test_binary = os.path.join(self.package_folder, "bin", "test_libsecret")
        if can_run(self):
            if str(self.settings.os) == "OHOS" and not self._prepare_ohos_runtime(test_binary):
                return
            # No conanrun env: its LD_LIBRARY_PATH points at the Conan cache
            # where the loader fails on symlinked libs; $ORIGIN RUNPATH wins.
            self.run(test_binary)
        else:
            self.output.info("Cross-building: consumer binary is run on OHOS device")

    def _prepare_ohos_runtime(self, binary):
        """E077 + HMDFS loader constraints:
        1. The OHOS loader cannot resolve shared libs through symlinks under
           the Conan cache; copy every NEEDED .so as a REAL file next to the
           binary ($ORIGIN is always loadable).
        2. Fresh/modified ELFs need a .codesign section to be executable.
        Returns False (with reason) if runtime validation cannot run."""
        import subprocess

        bindir = os.path.dirname(binary)
        objcopy = self._find_tool("llvm-objcopy")
        readelf = self._find_tool("llvm-readelf")
        signer = self._find_tool("binary-sign-tool")
        if not (objcopy and readelf and signer):
            self.output.info(
                "TARGET_RUNTIME_TESTS=NOT_RUN: OHOS signing tools unavailable"
            )
            self.output.info("CONSUMER_COMPILE_LINK_TESTS=1/1")
            return False

        def real_copy(src, dst):
            with open(src, "rb") as handle:
                data = handle.read()
            with open(dst, "wb") as handle:
                handle.write(data)

        # Search set = executable RUNPATH/RPATH dirs + every dependency package
        # libdir. A dependency lib's own NEEDED (e.g. libgcrypt -> libgpg-error)
        # cannot be resolved through that lib's RUNPATH (libs usually carry
        # none), so relying on the executable's RUNPATH alone drops the whole
        # transitive tail -> loader "Error relocating ... symbol not found".
        lib_dirs = []
        for dep in self.dependencies.values():
            if dep.package_folder:
                pkg_lib = os.path.join(dep.package_folder, "lib")
                if os.path.isdir(pkg_lib):
                    lib_dirs.append(pkg_lib)
        bin_dynamic = subprocess.run(
            [readelf, "-d", binary], capture_output=True, text=True
        ).stdout
        for line in bin_dynamic.splitlines():
            if "RUNPATH" in line or "RPATH" in line:
                for path in line.split("[")[-1].rstrip("]").split(":"):
                    if path and os.path.isdir(path):
                        lib_dirs.append(path)

        # Walk NEEDED chains from the test binary; copy each lib as a real
        # file beside it and sign it (loader rejects unsigned/invalid ELFs).
        pending = [binary]
        seen = set()
        while pending:
            current = pending.pop(0)
            real = os.path.realpath(current)
            if real in seen or not os.path.isfile(real):
                continue
            seen.add(real)
            output = subprocess.run(
                [readelf, "-d", real], capture_output=True, text=True
            ).stdout
            for line in output.splitlines():
                if "NEEDED" not in line:
                    continue
                needed = line.split("[")[-1].rstrip("]")
                dst = os.path.join(bindir, needed)
                if os.path.exists(dst):
                    pending.append(dst)
                    continue
                for lib_dir in lib_dirs:
                    candidate = os.path.join(lib_dir, needed)
                    if os.path.isfile(candidate):
                        real_copy(candidate, dst)
                        self._sign(dst, objcopy, signer)
                        pending.append(dst)
                        break
        return self._sign(binary, objcopy, signer)

    def _find_tool(self, name):
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = compiler_executables.get("c") or ""
        compiler_dir = (
            os.path.dirname(os.path.normpath(compiler)) if compiler else ""
        )
        candidates = [
            os.path.join(compiler_dir, name) if compiler_dir else "",
            os.path.join("/data/service/hnp/bin", name),
        ]
        for candidate in candidates + [shutil.which(name) or ""]:
            if candidate and os.path.isfile(candidate):
                return os.path.abspath(candidate)
        return ""

    def _sign(self, binary, objcopy, signer):
        """E077: remove stale .codesign, re-sign, restore exec bit."""
        import subprocess

        sections = subprocess.run(
            [self._find_tool("llvm-readelf"), "-S", binary],
            capture_output=True, text=True,
        ).stdout
        if ".codesign" in sections:
            subprocess.run(
                [objcopy, "--remove-section", ".codesign", binary], check=True
            )
        signed = binary + ".signed"
        result = subprocess.run(
            [signer, "sign", "-inFile", binary, "-outFile", signed,
             "-selfSign", "1"],
            capture_output=True, text=True,
        )
        if result.returncode != 0 or not os.path.isfile(signed):
            self.output.info(
                "TARGET_RUNTIME_TESTS=NOT_RUN: signing failed: {}".format(
                    (result.stderr or "").strip()[:200]
                )
            )
            self.output.info("CONSUMER_COMPILE_LINK_TESTS=1/1")
            return False
        os.chmod(signed, 0o755)
        os.replace(signed, binary)
        return True
