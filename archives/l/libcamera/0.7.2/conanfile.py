#!/usr/bin/env python3
"""Conan recipe for libcamera 0.7.2 on OpenHarmony arm64."""

import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, save
from conan.tools.gnu.pkgconfigdeps import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LibcameraConan(ConanFile):
    name = "libcamera"
    version = "0.7.2"
    description = "Complex Camera Support Library"
    license = "LGPL-2.1-or-later"
    homepage = "https://libcamera.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        # Upstream sets cpp_std=c++20 in its Meson project defaults.  Keep
        # Conan's package ID aligned with the actual ABI/API build even though
        # the shared OHOS profile defaults to cppstd=17.
        self.settings.compiler.cppstd = "20"
        if not self.options.shared:
            raise ConanException("libcamera upstream only builds shared libraries")

    def requirements(self):
        # libcamera's mandatory yaml-0.1 Meson dependency is provided by the
        # published libyaml recipe.  Optional Linux desktop/device dependencies
        # are deliberately disabled below.
        self.requires("libyaml/0.2.5")
        # IPA module signature verification needs libcrypto.  Use the
        # published OHOS-compatible OpenSSL package rather than relying on an
        # ambient host installation.
        self.requires("openssl/3.5.6")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        # libcamera's Mojo IPC generator imports PLY.  PLY is a host-side
        # build tool, not a target/runtime dependency, so keep it outside the
        # installed package and fetch the official PyPI sdist by checksum.
        ply_dir = os.path.join(self.source_folder, "_build_tools", "ply")
        get(self, **self.conan_data["build_tools"]["ply"],
            strip_root=True, destination=ply_dir)

    def generate(self):
        tc = MesonToolchain(self)
        # The OHOS worker exports LLVM tools under llvm-* names that Meson
        # cannot resolve reliably from PATH.  Pin the complete tool paths in
        # the generated native file, as required for clean Conan builds.
        tool_names = ("llvm-ar", "llvm-as", "llvm-strip", "llvm-nm",
                      "llvm-ranlib", "llvm-objcopy")
        tools = {name.removeprefix("llvm-"): shutil.which(name)
                 for name in tool_names}
        if self.settings.os == "OHOS":
            ohos_bin = "/data/service/hnp/bin"
            for name in tool_names:
                key = name.removeprefix("llvm-")
                if not tools[key]:
                    candidate = os.path.join(ohos_bin, name)
                    if os.path.isfile(candidate):
                        tools[key] = candidate
        missing = [name for name, path in tools.items() if not path]
        if missing:
            raise ConanException("Missing OHOS LLVM tools: " + ", ".join(missing))
        tc.ar = tools["ar"]
        tc.as_ = tools["as"]
        tc.strip = tools["strip"]
        tc.cpp_std = "c++20"
        for name in ("nm", "ranlib", "objcopy"):
            tc.binaries[name] = tools[name]
        tc.project_options["default_library"] = "shared"
        tc.project_options["werror"] = "false"
        tc.project_options["test"] = "true"
        tc.project_options["documentation"] = "disabled"
        tc.project_options["android"] = "disabled"
        tc.project_options["cam"] = "disabled"
        tc.project_options["gstreamer"] = "disabled"
        tc.project_options["pycamera"] = "disabled"
        tc.project_options["qcam"] = "disabled"
        tc.project_options["v4l2"] = "disabled"
        tc.project_options["tracing"] = "disabled"
        tc.project_options["udev"] = "disabled"
        tc.project_options["libdw"] = "disabled"
        tc.project_options["libunwind"] = "disabled"
        tc.project_options["pipelines"] = "uvcvideo"
        tc.generate()

        # Meson resolves yaml-0.1 through pkg-config, while libyaml's existing
        # Conan recipe exposes CMake metadata only.  Generate a truthful
        # pkg-config alias pointing at that already-published dependency.
        PkgConfigDeps(self).generate()
        yaml = self.dependencies["libyaml"]
        yaml_prefix = yaml.package_folder
        yaml_pc = os.path.join(self.generators_folder, "yaml-0.1.pc")
        save(self, yaml_pc, "\n".join([
            f"prefix={yaml_prefix}",
            "exec_prefix=${prefix}",
            "libdir=${prefix}/lib",
            "includedir=${prefix}/include",
            "",
            "Name: yaml-0.1",
            "Description: YAML parser and emitter library",
            "Version: 0.2.5",
            "Libs: -L${libdir} -lyaml",
            "Cflags: -I${includedir}",
            "",
        ]))

        # The OpenSSL recipe exposes CMake metadata, while libcamera probes
        # for libcrypto through pkg-config.  This alias points directly at
        # the Conan package selected above.
        openssl = self.dependencies["openssl"]
        openssl_prefix = openssl.package_folder
        crypto_pc = os.path.join(self.generators_folder, "libcrypto.pc")
        save(self, crypto_pc, "\n".join([
            f"prefix={openssl_prefix}",
            "exec_prefix=${prefix}",
            "libdir=${prefix}/lib",
            "includedir=${prefix}/include",
            "",
            "Name: libcrypto",
            "Description: OpenSSL cryptography library",
            "Version: 3.5.6",
            "Libs: -L${libdir} -lcrypto -ldl -pthread",
            "Cflags: -I${includedir}",
            "",
        ]))

        # The PLY sdist is a build-time Python import.  Inject it through the
        # Conan build environment rather than relying on an ambient shell.
        ply_path = os.path.join(self.source_folder, "_build_tools", "ply")
        self.buildenv_info.prepend_path("PYTHONPATH", ply_path)
        self.buildenv_info.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        VirtualBuildEnv(self).generate()

    @staticmethod
    def _is_elf(path):
        readelf = shutil.which("llvm-readelf") or "/data/service/hnp/bin/llvm-readelf"
        if not os.path.isfile(path) or not os.path.isfile(readelf):
            return False
        result = subprocess.run([readelf, "-h", path],
                                capture_output=True, text=True, check=False,
                                timeout=30)
        return result.returncode == 0 and "ELF" in result.stdout

    @staticmethod
    def _sign_ohos_elf(path):
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        readelf = shutil.which("llvm-readelf") or "/data/service/hnp/bin/llvm-readelf"
        if not os.path.isfile(path):
            return
        if not os.path.isfile(signer) or not os.path.isfile(readelf):
            raise ConanException("OHOS signing tools are required to execute libcamera tests")
        output = path + ".signed"
        subprocess.run([signer, "sign", "-inFile", path, "-outFile", output,
                        "-selfSign", "1"], check=True, timeout=120)
        sections = subprocess.run([readelf, "-SW", output], check=True,
                                  capture_output=True, text=True, timeout=30).stdout
        if sections.count(".codesign") != 1:
            raise ConanException(f"Signed ELF has invalid .codesign count: {path}")
        os.chmod(output, (os.stat(path).st_mode & 0o777) | 0o555)
        os.replace(output, path)

    def _sign_test_executables(self):
        if self.settings.os != "OHOS":
            return
        introspect = shutil.which("meson") or "meson"
        result = subprocess.run(
            [introspect, "introspect", self.build_folder, "--targets"],
            check=True, capture_output=True, text=True,
        )
        for target in json.loads(result.stdout):
            if target.get("type") != "executable":
                continue
            for filename in target.get("filename", []):
                if LibcameraConan._is_elf(filename):
                    self._sign_ohos_elf(filename)

    def build(self):
        apply_conandata_patches(self)
        # Meson invokes Python code generators directly during setup.  Apply
        # the private PLY and pkg-config paths to the actual Conan build
        # environment; buildenv_info alone describes package consumers and is
        # not sufficient for the recipe's own build step.
        environment = Environment()
        environment.prepend_path("PATH", "/system/bin")
        environment.prepend_path(
            "PYTHONPATH", os.path.join(self.source_folder, "_build_tools", "ply")
        )
        environment.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        environment.compose_env(VirtualBuildEnv(self).environment())
        with environment.vars(self).apply():
            meson = Meson(self)
            meson.configure()
            meson.build()
            # Upstream's complete Meson test graph is retained.  Camera/V4L2
            # fixtures may report their documented skip result when no device
            # is present; no test is silently removed or converted to a pass.
            if can_run(self):
                self._sign_test_executables()
                self.run(
                    f'meson test -C "{self.build_folder}" --print-errorlogs',
                    env=None,
                )
            else:
                raise ConanException("libcamera upstream tests cannot run for this target")

    def package(self):
        Meson(self).install()
        if self.settings.os == "OHOS":
            # Sign every installed ELF, including IPA modules and proxy
            # workers.  Symlinks are left intact and their real targets are
            # signed exactly once.
            for root, _, files in os.walk(self.package_folder):
                for filename in files:
                    path = os.path.join(root, filename)
                    if os.path.islink(path):
                        continue
                    if self._is_elf(path):
                        self._sign_ohos_elf(path)

    def package_info(self):
        # Conan library names omit the conventional ``lib`` prefix; the
        # installed files are libcamera.so and libcamera-base.so.
        self.cpp_info.libs = ["camera", "camera-base"]
        # Meson installs headers below include/libcamera/libcamera so the
        # public include root must be adjusted for <libcamera/...> includes.
        self.cpp_info.includedirs = ["include/libcamera"]
        self.cpp_info.set_property("cmake_file_name", "libcamera")
        self.cpp_info.set_property("cmake_target_name", "libcamera::libcamera")
        self.cpp_info.set_property("pkg_config_name", "libcamera")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.cxxflags.append("-std=c++20")
            self.cpp_info.system_libs = ["dl", "pthread"]
