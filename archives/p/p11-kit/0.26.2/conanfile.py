#!/usr/bin/env python3
"""Conan recipe for p11-kit 0.26.2 on HarmonyOS."""

import glob
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class P11KitConan(ConanFile):
    name = "p11-kit"
    version = "0.26.2"
    description = "PKCS#11 module loading and management library"
    license = "BSD-3-Clause"
    homepage = "https://github.com/p11-glue/p11-kit"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "shared-library"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(
            self,
            **self.conan_data["sources"][str(self.version)],
            strip_root=True,
        )

    def generate(self):
        toolchain = MesonToolchain(self)
        toolchain.project_options.update(
            {
                "wrap_mode": "nodownload",
                "libexecdir": "libexec",
                "hash_impl": "internal",
                "env_override_paths": "enabled",
                "libffi": "disabled",
                "closures": 64,
                "trust_module": "disabled",
                "systemd": "disabled",
                "bash_completion": "disabled",
                "zsh_completion": "disabled",
                "gtk_doc": False,
                "man": False,
                "nls": False,
                "test": True,
                "post_install_test": False,
            }
        )
        toolchain.generate()
        self._inject_archiver_tools()

    def build(self):
        apply_conandata_patches(self)
        self._prepare_build_environment()

        meson = Meson(self)
        meson.configure()
        meson.build()

        if can_run(self):
            tests = "test-version test-uri test-rpc test-rpc-message"
            command = "meson test -C {} --print-errorlogs {}".format(
                shlex.quote(self.build_folder), tests
            )
            self.run(command, env="conanbuild")
        else:
            self.output.info(
                "upstream core tests skipped: target executables cannot run on the build host"
            )

    def package(self):
        Meson(self).install()
        self._remove_server_subpackage()
        self._ensure_shared_object_aliases()
        self._sign_elf()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = ["p11-kit"]
        self.cpp_info.includedirs = ["include/p11-kit-1"]
        self.cpp_info.set_property("pkg_config_name", "p11-kit-1")
        self.cpp_info.set_property("cmake_file_name", "p11-kit")
        self.cpp_info.set_property("cmake_target_name", "p11-kit::p11-kit")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["dl", "pthread"]
        self.runenv_info.define_path(
            "P11_MODULE_PATH", os.path.join(self.package_folder, "lib", "pkcs11")
        )
        self.runenv_info.define_path(
            "P11_PACKAGE_CONFIG_MODULES",
            os.path.join(self.package_folder, "share", "p11-kit", "modules"),
        )
        self.runenv_info.define_path(
            "P11_SYSTEM_CONFIG_FILE",
            os.path.join(self.package_folder, "etc", "pkcs11", "pkcs11.conf"),
        )
        self.runenv_info.define_path(
            "P11_SYSTEM_CONFIG_MODULES",
            os.path.join(self.package_folder, "etc", "pkcs11", "modules"),
        )

    def _remove_server_subpackage(self):
        private_dir = os.path.join(self.package_folder, "libexec", "p11-kit")
        if os.path.isdir(private_dir):
            shutil.rmtree(private_dir)
        libexec_dir = os.path.dirname(private_dir)
        if os.path.isdir(libexec_dir) and not os.listdir(libexec_dir):
            os.rmdir(libexec_dir)

    def _ensure_shared_object_aliases(self):
        libdir = os.path.join(self.package_folder, "lib")
        candidates = [
            path
            for path in glob.glob(os.path.join(libdir, "libp11-kit.so.*"))
            if os.path.isfile(path) and not os.path.islink(path)
        ]
        if not candidates:
            raise ConanException("Meson installation did not produce a versioned libp11-kit")
        real_library = max(candidates, key=lambda path: len(os.path.basename(path)))

        # Some device workspaces cannot create links. Materialize only aliases
        # that Meson could not install, preserving normal links when supported.
        for filename in ("libp11-kit.so.0", "libp11-kit.so", "p11-kit-proxy.so"):
            target = os.path.join(libdir, filename)
            if os.path.isfile(target):
                continue
            if os.path.lexists(target):
                os.remove(target)
            shutil.copy2(real_library, target)

    def _sign_elf(self):
        if self.settings.os != "OHOS":
            return
        hnp_bin = "/data/service/hnp/bin"
        objcopy = os.path.join(hnp_bin, "llvm-objcopy")
        signer = os.path.join(hnp_bin, "binary-sign-tool")
        if not os.path.isfile(objcopy) or not os.path.isfile(signer):
            self.output.warning(
                "binary-sign-tool/llvm-objcopy unavailable; skipping ELF re-signing"
            )
            return

        patterns = ("bin/*", "lib/*.so", "lib/*.so.*", "lib/pkcs11/*.so")
        files = []
        for pattern in patterns:
            files.extend(glob.glob(os.path.join(self.package_folder, pattern)))
        for path in sorted(set(files)):
            if os.path.islink(path) or not os.path.isfile(path):
                continue
            try:
                with open(path, "rb") as handle:
                    if handle.read(4) != b"\x7fELF":
                        continue
            except OSError:
                continue
            self.run(
                '{objcopy} --remove-section .codesign "{path}" 2>/dev/null || true'.format(
                    objcopy=objcopy, path=path
                )
            )
            self.run(
                '{signer} sign -inFile "{path}" -outFile "{path}.signed" -selfSign 1'.format(
                    signer=signer, path=path
                )
            )
            if os.path.isfile(path + ".signed"):
                os.replace(path + ".signed", path)
                os.chmod(path, 0o755)

    def _prepare_build_environment(self):
        if self.settings.os != "OHOS":
            return

        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = compilers.get("c")
        if not compiler:
            raise ConanException(
                "tools.build:compiler_executables must define the C compiler"
            )
        compiler = os.path.realpath(compiler)
        llvm_lib = os.path.join(os.path.dirname(os.path.dirname(compiler)), "lib")
        if not os.path.isfile(os.path.join(llvm_lib, "libxml2.so.16")):
            raise ConanException(
                "OHOS SDK libxml2.so.16 not found beside compiler: {}".format(
                    llvm_lib
                )
            )

        # Some workers prepend ~/usr/local/lib, whose incompatible libxml2 can
        # shadow the SDK copy needed by lld. Keep the SDK runtime first.
        current_ld_path = os.environ.get("LD_LIBRARY_PATH", "")
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(
            path for path in (llvm_lib, current_ld_path) if path
        )

        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMP"] = tmpdir
        os.environ["TEMP"] = tmpdir

    def _inject_archiver_tools(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        ar = compilers.get("ar")
        ranlib = compilers.get("ranlib")
        cc = compilers.get("c") or ""
        compiler_dir = os.path.dirname(cc) if os.path.sep in cc else ""

        if not ar and compiler_dir:
            candidate = os.path.join(compiler_dir, "llvm-ar")
            if os.path.isfile(candidate):
                ar = candidate
        if not ranlib and compiler_dir:
            candidate = os.path.join(compiler_dir, "llvm-ranlib")
            if os.path.isfile(candidate):
                ranlib = candidate

        for filename in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            toolchain_file = os.path.join(self.generators_folder, filename)
            if not os.path.isfile(toolchain_file):
                continue
            with open(toolchain_file, encoding="utf-8") as handle:
                content = handle.read()
            if "[binaries]" not in content:
                continue

            entries = []
            if ar and "\nar =" not in content:
                entries.append("ar = '{}'".format(ar))
            if ranlib and "\nranlib =" not in content:
                entries.append("ranlib = '{}'".format(ranlib))
            if entries:
                insertion = "[binaries]\n" + "\n".join(entries) + "\n"
                with open(toolchain_file, "w", encoding="utf-8") as handle:
                    handle.write(content.replace("[binaries]\n", insertion, 1))
