#!/usr/bin/env python3
"""Conan recipe for ONNX Runtime (CMake, OHOS cross-compile).

ONNX Runtime uses CMake with FetchContent for dependencies. This recipe:
1. Downloads source from GitHub release tarball
2. Pre-downloads FetchContent dependencies to local mirror
3. Builds protoc from protobuf source (host protoc for cross-compile)
4. Configures CMake with OHOS NDK toolchain
5. Patches cpuinfo after FetchContent extraction (OHOS→Linux alias)
6. Builds shared library

Source modifications applied via conandata patches:
- patch command options (toybox patch compatibility)
- add_compile_options for BF16/FP16 ARM extensions
- mlasi.h BF16 guard
- env.cc musl pthread_setaffinity_np guard
- flatbuffers patch skip on OHOS
"""
import os
import shutil
import subprocess
import zipfile
from pathlib import Path
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, download, apply_conandata_patches, export_conandata_patches


class OnnxruntimeConan(ConanFile):
    name = "onnxruntime"
    version = "1.27.1"
    description = "ONNX Runtime: cross-platform, high performance ML inferencing accelerator"
    license = "MIT"
    homepage = "https://onnxruntime.ai"
    url = "https://github.com/microsoft/onnxruntime"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # OHOS toolchain is provided by the profile; CMakeToolchain generates the toolchain file
        # We need to pass the OHOS NDK toolchain via VCPKG_CHAINLOAD_TOOLCHAIN_FILE or directly
        tc.generate()

    def build(self):
        # Apply source patches (patch options, BF16/FP16, mlasi.h, env.cc, flatbuffers)
        apply_conandata_patches(self)

        # Step 1: Pre-download FetchContent dependencies to local mirror
        self._download_deps()

        # Step 2: Build protoc from protobuf source (needed for cross-compile)
        protoc_path = self._build_protoc()

        # Step 3: Configure CMake
        cmake = CMake(self)
        ohos_toolchain = self._get_ohos_toolchain()

        cmake_args = [
            f"-DCMAKE_TOOLCHAIN_FILE={ohos_toolchain}",
            "-DOHOS_ARCH=arm64-v8a",
            f"-DCMAKE_AR={self._find_tool('llvm-ar')}",
            f"-DCMAKE_RANLIB={self._find_tool('llvm-ranlib')}",
            "-Donnxruntime_BUILD_SHARED_LIB=ON",
            "-Donnxruntime_BUILD_UNIT_TESTS=OFF",
            "-Donnxruntime_ENABLE_PYTHON=OFF",
            "-Donnxruntime_MINIMAL_BUILD=ON",
            "-Donnxruntime_DISABLE_CONTRIB_OPS=OFF",
            "-Donnxruntime_USE_NNAPI_BUILTIN=OFF",
            "-Donnxruntime_BUILD_JAVA=OFF",
            "-Donnxruntime_BUILD_CSHARP=OFF",
            "-Donnxruntime_BUILD_OBJC=OFF",
            f"-DONNX_CUSTOM_PROTOC_EXECUTABLE={protoc_path}",
            f"-Donnxruntime_CMAKE_DEPS_MIRROR_DIR={self._get_mirror_dir()}",
        ]

        # Configure with extra args - ONNX Runtime's CMakeLists.txt is in cmake/ subdir
        cmake.configure(build_script_folder="cmake", cli_args=cmake_args)

        # Step 4: Patch cpuinfo after FetchContent extraction (OHOS not recognized)
        self._patch_cpuinfo()

        # Step 5: Build
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["onnxruntime"]
        self.cpp_info.set_property("cmake_file_name", "onnxruntime")
        self.cpp_info.set_property("pkg_config_name", "onnxruntime")

    # ─── Helper methods ──────────────────────────────────────────────

    def _get_source_dir(self):
        return Path(self.source_folder)

    def _get_mirror_dir(self):
        return self._get_source_dir() / "mirror"

    def _get_ohos_toolchain(self):
        """Find the OHOS NDK CMake toolchain file."""
        # Look for OHOS SDK in standard location
        sdk_root = Path("/data/service/hnp/ohos-sdk.org")
        if sdk_root.exists():
            for sdk_dir in sorted(sdk_root.iterdir(), reverse=True):
                toolchain = sdk_dir / "ohos" / "native" / "build" / "cmake" / "ohos.toolchain.cmake"
                if toolchain.exists():
                    return str(toolchain)
        raise RuntimeError("OHOS NDK toolchain not found")

    def _find_tool(self, name):
        """Find a tool in PATH."""
        path = shutil.which(name)
        if path:
            return path
        # Check common OHOS locations
        for d in ["/data/service/hnp/bin", "/usr/bin", "/usr/local/bin"]:
            p = Path(d) / name
            if p.exists():
                return str(p)
        raise RuntimeError(f"Tool '{name}' not found")

    def _get_mirror_urls(self, url):
        """Return list of mirror URLs for a GitHub URL (matching CI fallback)."""
        if not url.startswith("https://github.com/"):
            return [url]
        return [
            "https://gh-proxy.com/" + url,
            "https://mirror.ghproxy.com/" + url,
            "https://ghproxy.com/" + url,
            "https://gitclone.com/" + url[len("https://"):],
            "https://moeyy.cn/gh-proxy/" + url,
            url.replace("https://github.com", "https://kkgithub.com"),
            url,
        ]

    def _download_with_mirrors(self, url, dest_path):
        """Download a file trying mirror URLs in order (CI worker can't reach github.com)."""
        mirrors = self._get_mirror_urls(url)
        last_err = None
        for mirror_url in mirrors:
            try:
                download(self, mirror_url, dest_path)
                return
            except Exception as e:
                last_err = e
                self.output.warn(f"  download failed from {mirror_url}: {e}")
                continue
        raise last_err

    def _download_deps(self):
        """Pre-download FetchContent dependencies to local mirror directory."""
        mirror = self._get_mirror_dir()
        deps_file = self._get_source_dir() / "cmake" / "deps.txt"

        # Check for pre-existing mirror from manual build
        prebuilt_mirror = Path.home() / "builds" / "onnxruntime-1.27.1.work" / "mirror"
        if prebuilt_mirror.exists():
            self.output.info(f"Using pre-built mirror from {prebuilt_mirror}")
            if not mirror.exists():
                mirror.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(str(prebuilt_mirror), str(mirror), dirs_exist_ok=True)
            return

        # Parse deps.txt and download required dependencies using Conan's download()
        required_deps = [
            "abseil_cpp", "protobuf", "onnx", "re2", "safeint",
            "microsoft_gsl", "date", "eigen", "pytorch_cpuinfo",
            "mp11", "json", "flatbuffers",
        ]

        with open(deps_file) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split(";")
                if len(parts) < 3:
                    continue
                name, url, _ = parts[0], parts[1], parts[2]
                if name not in required_deps:
                    continue

                if not url.startswith("https://"):
                    continue
                local_path = mirror / url[8:]

                if local_path.exists():
                    continue

                local_path.parent.mkdir(parents=True, exist_ok=True)
                self.output.info(f"Downloading {name} from {url}...")
                tmp_path = local_path.with_suffix(".tmp")
                self._download_with_mirrors(url, str(tmp_path))
                shutil.move(str(tmp_path), str(local_path))
                self.output.info(f"  Downloaded {name}: {local_path.stat().st_size} bytes")

    def _build_protoc(self):
        """Build protoc from protobuf source for host platform."""
        mirror = self._get_mirror_dir()
        proto_zip = mirror / "github.com" / "protocolbuffers" / "protobuf" / "archive" / "refs" / "tags" / "v21.12.zip"

        # Download protobuf source if not in mirror
        if not proto_zip.exists():
            self.output.info("Protobuf not in mirror, downloading directly...")
            proto_zip.parent.mkdir(parents=True, exist_ok=True)
            url = "https://github.com/protocolbuffers/protobuf/archive/refs/tags/v21.12.zip"
            tmp_path = proto_zip.with_suffix(".tmp")
            self._download_with_mirrors(url, str(tmp_path))
            shutil.move(str(tmp_path), str(proto_zip))
            self.output.info(f"Downloaded protobuf: {proto_zip.stat().st_size} bytes")

        # Extract protobuf
        proto_build_dir = Path(self.build_folder) / "protobuf-protoc"
        proto_build_dir.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(proto_zip) as zf:
            zf.extractall(proto_build_dir)

        proto_src = proto_build_dir / "protobuf-21.12"

        # Build just protoc using native compiler
        cc = self._find_tool("clang")
        cxx = self._find_tool("clang++")
        cmake_bin = self._find_tool("cmake")

        build_dir = proto_src / "build-protoc"
        build_dir.mkdir(parents=True, exist_ok=True)

        subprocess.run([
            cmake_bin, str(proto_src), "-B", str(build_dir),
            f"-DCMAKE_C_COMPILER={cc}",
            f"-DCMAKE_CXX_COMPILER={cxx}",
            "-DCMAKE_BUILD_TYPE=Release",
            "-Dprotobuf_BUILD_TESTS=OFF",
            "-Dprotobuf_BUILD_SHARED_LIBS=OFF",
        ], check=True)

        subprocess.run([
            cmake_bin, "--build", str(build_dir), "--target", "protoc",
            "-j", str(os.cpu_count())
        ], check=True)

        protoc_path = build_dir / "protoc"
        if not protoc_path.exists():
            candidates = list(build_dir.glob("protoc-*"))
            if not candidates:
                raise RuntimeError(f"protoc binary not found in {build_dir}")
            protoc_path = candidates[0]

        self.output.info(f"Built protoc at {protoc_path}")
        return str(protoc_path)

    def _patch_cpuinfo(self):
        """Patch cpuinfo CMakeLists.txt to recognize OHOS as Linux."""
        build_dir = Path(self.build_folder)
        cpuinfo_cmake = build_dir / "_deps" / "pytorch_cpuinfo-src" / "CMakeLists.txt"

        if not cpuinfo_cmake.exists():
            self.output.warn("cpuinfo CMakeLists.txt not found, skipping patch")
            return

        content = cpuinfo_cmake.read_text()
        if "OHOS" in content:
            self.output.info("cpuinfo already patched for OHOS")
            return

        # Add OHOS to Linux matches
        original = content
        content = content.replace(
            'STREQUAL "Linux" OR CMAKE_SYSTEM_NAME STREQUAL "Android"',
            'STREQUAL "Linux" OR CMAKE_SYSTEM_NAME STREQUAL "Android" OR CMAKE_SYSTEM_NAME STREQUAL "OHOS"'
        )
        content = content.replace(
            '^(Windows|WindowsStore|CYGWIN|MSYS|Darwin|Linux|Android|FreeBSD|Emscripten)$',
            '^(Windows|WindowsStore|CYGWIN|MSYS|Darwin|Linux|Android|FreeBSD|Emscripten|OHOS)$'
        )

        if content == original:
            self.output.warn("cpuinfo patch had no effect (patterns not found)")
        else:
            cpuinfo_cmake.write_text(content)
            self.output.info("Patched cpuinfo CMakeLists.txt for OHOS")
