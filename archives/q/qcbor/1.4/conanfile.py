from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches

import glob
import os
import shutil
import subprocess


class QcborConan(ConanFile):
    name = "qcbor"
    version = "1.4"
    description = "QCBOR: comprehensive, powerful, commercial-grade CBOR (RFC 8949) encode/decode library"
    license = "BSD-3-Clause"
    homepage = "https://github.com/laurencelundblade/QCBOR"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # Upstream registers no add_test(); BUILD_QCBOR_TEST=APP builds the
        # qcbortest aggregator binary we run directly in build().
        tc.variables["BUILD_QCBOR_TEST"] = "APP"
        tc.variables["CMAKE_SKIP_INSTALL_RPATH"] = "ON"
        tc.user_presets_path = False
        tc.generate()

    @staticmethod
    def _ohos_tool(name, fallback):
        return shutil.which(name) or fallback

    def _sign_ohos_elf(self, path):
        # E077: linked ELFs carry an unsigned placeholder .codesign section;
        # strip it first, sign without the toolchain LD_LIBRARY_PATH, verify.
        signer = self._ohos_tool("binary-sign-tool", "/data/service/hnp/bin/binary-sign-tool")
        readelf = self._ohos_tool("llvm-readelf", "/data/service/hnp/bin/llvm-readelf")
        objcopy = self._ohos_tool("llvm-objcopy", "/data/service/hnp/bin/llvm-objcopy")
        if not (os.path.isfile(signer) and os.path.isfile(readelf) and os.path.isfile(objcopy)):
            self.output.warning("OHOS signing tools missing; running qcbortest unsigned")
            return
        sections = subprocess.run(
            [readelf, "-SW", path], capture_output=True, text=True, timeout=30
        ).stdout
        if ".codesign" in sections:
            subprocess.run(
                [objcopy, "--remove-section", ".codesign", path],
                check=True, timeout=60,
            )
        env = dict(os.environ)
        env.pop("LD_LIBRARY_PATH", None)
        subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", path + ".signed", "-selfSign", "1"],
            check=True, timeout=60, env=env,
        )
        os.replace(path + ".signed", path)

    def _run_upstream_test_suite(self):
        candidates = glob.glob(
            os.path.join(self.build_folder, "**", "qcbortest"), recursive=True
        )
        if not candidates:
            raise ConanException("qcbortest aggregator binary not found in build tree")
        exe = candidates[0]
        self._sign_ohos_elf(exe)
        os.chmod(exe, 0o755)
        # OHOS exec gate: the first exec of a fresh binary can be swallowed
        # (empty stdout, rc=0); a later identical exec is let through.
        ret = None
        for attempt in range(3):
            ret = subprocess.run(
                [exe], capture_output=True, text=True, timeout=1800,
                cwd=os.path.dirname(exe),
            )
            if ret.returncode == 0 and ret.stdout.strip():
                break
            self.output.info(f"qcbortest attempt {attempt + 1}: rc={ret.returncode}")
        if ret is None or ret.returncode != 0 or not ret.stdout.strip():
            tail = "\n".join((ret.stdout + ret.stderr).splitlines()[-30:])
            raise ConanException(f"qcbortest failed rc={ret.returncode}\n{tail}")
        lines = [ln for ln in ret.stdout.splitlines() if ln.strip()]
        self.output.info(f"qcbortest summary: {lines[-1].strip()}")

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_test_suite()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["qcbor"]
