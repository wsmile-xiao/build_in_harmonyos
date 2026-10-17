"""KDSoap 2.3.0 for HarmonyOS PC."""

import os
import platform
import shutil
import stat
import subprocess
import tempfile
import hashlib

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualRunEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, unzip


class KDSoapConan(ConanFile):
    name = "kdsoap"
    version = "2.3.0"
    description = "Qt-based SOAP client, server, and WSDL compiler"
    license = "MIT"
    homepage = "https://github.com/KDAB/KDSoap"
    url = "https://github.com/KDAB/KDSoap"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def requirements(self):
        # The 6.11.1.3 package_info requires patchelf on the consumer host;
        # the published 6.11.1 package provides the required Qt modules.
        self.requires("qtbase/6.11.1")

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        source = self.conan_data["sources"]
        local_archive = os.environ.get("KDSOAP_SOURCE_ARCHIVE")
        if local_archive:
            with open(local_archive, "rb") as stream:
                actual = hashlib.file_digest(stream, "sha256").hexdigest()
            if actual.lower() != source["sha256"].lower():
                raise ConanException("KDSoap source archive SHA-256 mismatch")
            unzip(self, local_archive, destination=self.source_folder, strip_root=True)
        else:
            get(self, **source, strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        CMakeDeps(self).generate()
        VirtualRunEnv(self).generate()
        qt_cmake = os.path.join(self.dependencies["qtbase"].package_folder, "lib", "cmake")
        tc = CMakeToolchain(self)
        for component in ("Qt6", "Qt6Core", "Qt6CoreTools", "Qt6Network", "Qt6Xml", "Qt6Test"):
            tc.cache_variables[f"{component}_DIR"] = os.path.join(qt_cmake, component)
        tc.variables["KDSoap_QT6"] = "ON"
        tc.variables["KDSoap_STATIC"] = "OFF" if self.options.shared else "ON"
        tc.variables["KDSoap_TESTS"] = "ON"
        tc.variables["KDSoap_EXAMPLES"] = "OFF"
        tc.variables["KDSoap_DOCS"] = "OFF"
        tc.cache_variables["CMAKE_SKIP_RPATH"] = "ON"
        tc.generate()

    def _runtime_env(self):
        env = Environment()
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(self.dependencies["qtbase"].package_folder, "lib"))
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(self.build_folder, "lib"))
        env.define("QT_QPA_PLATFORM", "offscreen")
        return env

    def build(self):
        cmake = CMake(self)
        with self._runtime_env().vars(self).apply():
            cmake.configure()
            cmake.build(build_tool_args=["-j1"])
            if can_run(self) and platform.system() == "HarmonyOS":
                self.run(
                    'ctest --test-dir "{}" --output-on-failure --no-tests=error --timeout 60 -j1'.format(self.build_folder)
                )

    def package(self):
        CMake(self).install()
        if str(self.settings.os) == "OHOS":
            self._sign_installed_elfs()

    def _sign_installed_elfs(self):
        signer = shutil.which("binary-sign-tool")
        if not signer:
            raise ConanException("binary-sign-tool is required for installed OHOS ELF files")
        for root, _, files in os.walk(self.package_folder):
            for name in files:
                binary = os.path.join(root, name)
                if os.path.islink(binary):
                    continue
                with open(binary, "rb") as stream:
                    header = stream.read(18)
                if len(header) < 18 or header[:4] != b"\x7fELF":
                    continue
                byte_order = {1: "little", 2: "big"}.get(header[5])
                if not byte_order or int.from_bytes(header[16:18], byte_order) not in (2, 3):
                    continue
                mode = stat.S_IMODE(os.stat(binary).st_mode)
                with tempfile.TemporaryDirectory(prefix=".kdsoap-sign-", dir=root) as temp:
                    signed = os.path.join(temp, "signed")
                    result = subprocess.run(
                        [signer, "sign", "-inFile", binary, "-outFile", signed, "-selfSign", "1"],
                        capture_output=True, text=True, timeout=120,
                    )
                    if result.returncode or not os.path.isfile(signed):
                        raise ConanException("Signing {} failed: {}".format(binary, result.stderr or result.stdout))
                    with open(signed, "rb") as stream:
                        if stream.read(4) != b"\x7fELF":
                            raise ConanException("Signing {} produced a non-ELF file".format(binary))
                    os.replace(signed, binary)
                    os.chmod(binary, mode | 0o755)

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["kdsoap-server-qt6", "kdsoap-qt6"]
        self.cpp_info.requires = ["qtbase::core", "qtbase::network", "qtbase::xml"]
        self.runenv_info.prepend_path("LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))
