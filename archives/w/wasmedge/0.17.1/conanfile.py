import os
import shutil
import tempfile

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class WasmEdgeConan(ConanFile):
    name = "wasmedge"
    version = "0.17.1"
    description = "WasmEdge is a lightweight, high-performance WebAssembly runtime"
    license = "Apache-2.0"
    homepage = "https://github.com/WasmEdge/WasmEdge"
    url = "https://github.com/WasmEdge/WasmEdge"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def layout(self):
        cmake_layout(self)

    def source(self):
        try:
            get(self, **self.conan_data["sources"], strip_root=True)
        except ConanException:
            self.output.warning(
                "Falling back to GitCode mirror for wasmedge after official tarball download failed"
            )
            self._clone_mirror(
                "https://gitcode.com/gh_mirrors/wa/WasmEdge.git",
                "0.17.1",
                self.source_folder,
            )
        third_party = {
            "fmt": (
                [
                    "https://github.com/fmtlib/fmt/archive/refs/tags/11.0.2.tar.gz",
                ],
                "6cb1e6d37bdcb756dbbe59be438790db409cdb4868c66e888d5df9f13f7c027f",
            ),
            "spdlog": (
                [
                    "https://github.com/gabime/spdlog/archive/refs/tags/v1.13.0.tar.gz",
                ],
                "534f2ee1a4dcbeb22249856edfb2be76a1cf4f708a20b0ac2ed090ee24cfdbc9",
            ),
            "simdjson": (
                [
                    "https://github.com/simdjson/simdjson/archive/refs/tags/v3.10.0.tar.gz",
                ],
                "9c30552f1dd0ee3d0832bb1c6b7b97d813b18d5ef294c10dcb6fc242e5947de8",
            ),
            "stb": (
                [
                    "https://github.com/nothings/stb/archive/2dfbe86bef853be33cbbda07abcb4db58c7f817d.tar.gz",
                ],
                "f8803386a38269bb4ac3088bbf6b3ebc4ea3072a1bcc9bfdd59ccfc5d66550eb",
                "https://gitcode.com/gh_mirrors/st/stb.git",
                "2dfbe86bef853be33cbbda07abcb4db58c7f817d",
            ),
        }
        for name, metadata in third_party.items():
            destination = os.path.join(self.source_folder, "third_party", name)
            urls, sha256 = metadata[:2]
            try:
                get(
                    self,
                    url=urls,
                    sha256=sha256,
                    destination=destination,
                    strip_root=True,
                    filename=f"{name}.tar.gz",
                )
            except ConanException:
                if len(metadata) < 4:
                    raise
                mirror_repo, mirror_ref = metadata[2:]
                self.output.warning(
                    f"Falling back to GitCode mirror for {name} after official tarball download failed"
                )
                self._clone_mirror(mirror_repo, mirror_ref, destination)

    def _clone_mirror(self, repo_url, ref, destination):
        tmpdir = tempfile.mkdtemp(prefix=f"{self.name}-mirror-")
        clone_dir = os.path.join(tmpdir, "src")
        try:
            shutil.rmtree(destination, ignore_errors=True)
            self.run(f'git clone --filter=blob:none --no-checkout "{repo_url}" "{clone_dir}"')
            self.run(f'git -C "{clone_dir}" checkout --detach "{ref}"')
            shutil.rmtree(os.path.join(clone_dir, ".git"), ignore_errors=True)
            shutil.copytree(clone_dir, destination)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["WASMEDGE_BUILD_TESTS"] = "OFF"
        tc.variables["WASMEDGE_BUILD_COVERAGE"] = "OFF"
        tc.variables["WASMEDGE_BUILD_SHARED_LIB"] = "ON" if self.options.shared else "OFF"
        tc.variables["WASMEDGE_BUILD_STATIC_LIB"] = "OFF" if self.options.shared else "ON"
        tc.variables["WASMEDGE_BUILD_TOOLS"] = "OFF"
        tc.variables["WASMEDGE_BUILD_PLUGINS"] = "OFF"
        tc.variables["WASMEDGE_BUILD_EXAMPLE"] = "OFF"
        tc.variables["WASMEDGE_BUILD_WASI_NN_RPC"] = "OFF"
        tc.variables["WASMEDGE_USE_LLVM"] = "OFF"
        tc.variables["WASMEDGE_FORCE_DISABLE_LTO"] = "ON"
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = bool(self.options.get_safe("fPIC", True))
        tc.extra_cxxflags.extend(["-Wno-error=maybe-uninitialized", "-Wno-error=array-bounds"])
        third_party = os.path.join(self.source_folder, "third_party")
        tc.variables["FETCHCONTENT_SOURCE_DIR_FMT"] = os.path.join(third_party, "fmt")
        tc.variables["FETCHCONTENT_SOURCE_DIR_SPDLOG"] = os.path.join(third_party, "spdlog")
        tc.variables["FETCHCONTENT_SOURCE_DIR_SIMDJSON"] = os.path.join(third_party, "simdjson")
        tc.variables["FETCHCONTENT_SOURCE_DIR_STB"] = os.path.join(third_party, "stb")
        tc.generate()

    def build(self):
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["wasmedge"]
        self.cpp_info.bindirs = []
