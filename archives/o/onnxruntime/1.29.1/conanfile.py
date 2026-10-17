#!/usr/bin/env python3
"""Conan recipe for ONNX Runtime 1.29.1 (CMake, OHOS cross-compile).

ONNX Runtime uses CMake with FetchContent for dependencies. This recipe:
1. Downloads source from the GitHub release tarball
2. Pre-downloads FetchContent dependencies to a local mirror
3. Builds protoc from protobuf source (host protoc for the cross build)
4. Configures CMake with the OHOS NDK toolchain
5. Patches cpuinfo after FetchContent extraction (OHOS→Linux alias)
6. Builds the shared library

WHAT CHANGED FOR 1.29.1 (re-verified against the source tree; see notes.md)
  - `cmake_minimum_required` is now **3.28** (cmake/CMakeLists.txt:6).
  - The C++ standard floor is now **20** and is enforced with FATAL_ERROR
    (cmake/onnxruntime_language_standard_versions.cmake:9,48-65).
  - There is still **no top-level CMakeLists.txt** — `cmake/` remains the only
    entry point, so build_script_folder="cmake" stays correct.
  - `onnxruntime_MINIMAL_BUILD` defaults OFF, but turning it ON now *silently*
    implies `DISABLE_EXCEPTIONS=ON` + `DISABLE_RTTI=ON` (cmake_dependent_option
    at cmake/CMakeLists.txt:200,202).  This recipe builds the **full** operator
    set (MINIMAL_BUILD=OFF) and keeps exceptions/RTTI ON, so no core runtime
    capability is traded away for build time.
  - `ONNX_CUSTOM_PROTOC_EXECUTABLE` is still required for a cross build
    (cmake/external/protobuf_function.cmake:40-45): without it the just-built
    aarch64 `protoc` would be executed on the build host.  Upstream can
    FetchContent a prebuilt protoc (onnxruntime_external_deps.cmake:114-172)
    but building it from source, as here, is the offline-safe route.
  - flatbuffers: `FLATBUFFERS_BUILD_FLATC` is forced OFF only for
    iOS/tvOS/visionOS/Android/Emscripten (onnxruntime_external_deps.cmake:449-452)
    — OHOS is not in that list, so a cross-compiled aarch64 flatc would be
    built as an ALL dependency.  Passed explicitly OFF here.  The generated
    flatbuffer headers are committed upstream (core/flatbuffers/schema/*.fbs.h),
    so no flatc is needed.
  - `onnxruntime_USE_PREINSTALLED_EIGEN` is dead (its only occurrence in the
    tree is its own declaration); Eigen is always fetched.  Left at default.

Source modifications applied via conandata patches (re-baselined onto 1.29.1):
- patch command options (toybox patch compatibility: -l instead of
  --binary --ignore-whitespace)
- add_compile_options for BF16/FP16 ARM extensions + warning suppression
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
    version = "1.29.1"
    description = "ONNX Runtime: cross-platform, high performance ML inferencing accelerator"
    license = "MIT"
    homepage = "https://onnxruntime.ai"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        # ONNX Runtime 1.29.1 requires C++20 and raises the standard itself
        # (onnxruntime_language_standard_versions.cmake:48-65); set it here so
        # the Conan profile and the CMake build agree.
        self.settings.compiler.cppstd = "20"

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def _apply_ohos_libcxx_fallbacks(self):
        """Replace library facilities the OHOS libc++ (15.0.4) does not have.

        MLAS uses std::make_unique_for_overwrite<int8_t[]>, which is a C++23
        library facility; the OHOS SDK ships _LIBCPP_VERSION 15004 and fails
        with (measured with -std=c++20 on the device):

          onnxruntime/core/mlas/lib/qlutgemm.cpp:475:28: error: no member named
          'make_unique_for_overwrite' in namespace 'std'

        <memory> is already included, so this is a library-version gap, not a
        missing header.  std::unique_ptr<T[]>(new T[n]) is the exact equivalent
        that make_unique_for_overwrite is specified in terms of (default
        initialisation, i.e. indeterminate values for int8_t; the buffer is
        memset right afterwards in any case).

        Idempotent: a second run finds the replacement and does nothing.
        """
        target = os.path.join(self.source_folder, "onnxruntime", "core", "mlas",
                              "lib", "qlutgemm.cpp")
        needle = "    auto lut_buffer = std::make_unique_for_overwrite<int8_t[]>(lut_buffer_size);\n"
        replacement = (
            "    // OHOS: std::make_unique_for_overwrite is C++23; libc++ 15.0.4 (OHOS SDK)\n"
            "    // does not provide it.  Same semantics: default-initialised array.\n"
            "    auto lut_buffer = std::unique_ptr<int8_t[]>(new int8_t[lut_buffer_size]);\n"
        )
        with open(target, encoding="utf-8") as fh:
            text = fh.read()
        if replacement in text:
            self.output.info("qlutgemm.cpp: libc++ fallback already applied")
            return
        if needle not in text:
            raise ConanException(
                "qlutgemm.cpp: expected std::make_unique_for_overwrite call site not found")
        with open(target, "w", encoding="utf-8") as fh:
            fh.write(text.replace(needle, replacement, 1))
        self.output.info("qlutgemm.cpp: std::make_unique_for_overwrite replaced")


    def _apply_clang15_lambda_fallbacks(self):
        """Rewrite structured-binding captures clang 15 cannot compile.

        onnxruntime/core/session/model_editor_c_api.cc declares

            auto [ptr_it, ptr_inserted] = graph->initializer_ptrs.insert(tensor);

        and later uses `ptr_it` inside a `[&]` lambda in the ORT_CATCH block.
        Capturing a structured binding in a lambda is P1091R3, a C++20 feature
        that clang 15 does not implement -- even though the target is compiled
        with -std=gnu++20, clang reports

          error: reference to local binding 'ptr_it' declared in enclosing function

        (measured on the device, clang version 15, onnxruntime 1.29.1).
        Binding the two members to ordinary locals makes the `[&]` capture
        well-formed and is semantically identical.

        Idempotent: a second run finds the replacement and does nothing.
        """
        target = os.path.join(self.source_folder, "onnxruntime", "core",
                              "session", "model_editor_c_api.cc")
        sites = [
            (
                "  auto [ptr_it, ptr_inserted] = graph->initializer_ptrs.insert(tensor);\n",
                "  // OHOS: clang 15 lacks P1091R3, so `ptr_it` below cannot be captured by the\n"
                "  // [&] lambda in ORT_CATCH.  Bind the members to ordinary locals instead.\n"
                "  auto ptr_result = graph->initializer_ptrs.insert(tensor);\n"
                "  auto ptr_it = ptr_result.first;\n"
                "  const bool ptr_inserted = ptr_result.second;\n",
            ),
            (
                "  auto [ptr_it, ptr_inserted] = graph->node_ptrs.insert(node);\n",
                "  // OHOS: see AddInitializerToGraph -- clang 15 lacks P1091R3.\n"
                "  auto ptr_result = graph->node_ptrs.insert(node);\n"
                "  auto ptr_it = ptr_result.first;\n"
                "  const bool ptr_inserted = ptr_result.second;\n",
            ),
        ]
        with open(target, encoding="utf-8") as fh:
            text = fh.read()
        applied = 0
        for needle, replacement in sites:
            if replacement in text:
                continue
            if text.count(needle) != 1:
                raise ConanException(
                    "model_editor_c_api.cc: expected exactly 1 occurrence of %r, found %d"
                    % (needle.strip(), text.count(needle)))
            text = text.replace(needle, replacement, 1)
            applied += 1
        if applied == 0:
            self.output.info("model_editor_c_api.cc: clang15 lambda fallback already applied")
            return
        with open(target, "w", encoding="utf-8") as fh:
            fh.write(text)
        self.output.info("model_editor_c_api.cc: %d structured-binding capture(s) rewritten"
                         % applied)

    def build(self):
        # Apply source patches (patch options, mlasi.h, env.cc, flatbuffers)
        apply_conandata_patches(self)
        # BF16/FP16 march flags for the onnxruntime_mlas target — applied in
        # place rather than as a conandata patch, see _patch_mlas_cmake().
        self._patch_mlas_cmake()
        # C++23 facilities the OHOS libc++ lacks (see the method's docstring).
        self._apply_ohos_libcxx_fallbacks()
        # clang 15 cannot capture a structured binding in a lambda (P1091R3).
        self._apply_clang15_lambda_fallbacks()

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
            "-DCMAKE_CXX_STANDARD=20",
            "-Donnxruntime_BUILD_SHARED_LIB=ON",
            "-Donnxruntime_BUILD_UNIT_TESTS=OFF",
            "-Donnxruntime_ENABLE_PYTHON=OFF",
            # 不使用 MINIMAL_BUILD：保留完整算子集与正常的运行时能力。
            # 1.29.1 中 MINIMAL_BUILD=ON 还会连带 DISABLE_EXCEPTIONS/RTTI=ON。
            "-Donnxruntime_MINIMAL_BUILD=OFF",
            "-Donnxruntime_DISABLE_EXCEPTIONS=OFF",
            "-Donnxruntime_DISABLE_RTTI=OFF",
            "-Donnxruntime_DISABLE_CONTRIB_OPS=OFF",
            "-Donnxruntime_USE_NNAPI_BUILTIN=OFF",
            "-Donnxruntime_BUILD_JAVA=OFF",
            "-Donnxruntime_BUILD_CSHARP=OFF",
            "-Donnxruntime_BUILD_OBJC=OFF",
            # flatbuffers: OHOS 不在上游自动关闭 flatc 的平台名单里，显式关闭
            "-DFLATBUFFERS_BUILD_FLATC=OFF",
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
            # Direct first: the farm worker reaches github through the relay
            # proxy (192.168.43.16:18899).  The public mirrors below are kept
            # only as a fallback -- several of them answer with an HTML index
            # page and HTTP 200, which silently poisons the FetchContent
            # mirror directory with a valid-looking but useless file.
            url,
            "https://gh-proxy.com/" + url,
            "https://mirror.ghproxy.com/" + url,
            "https://ghproxy.com/" + url,
            "https://gitclone.com/" + url[len("https://"):],
            "https://moeyy.cn/gh-proxy/" + url,
            url.replace("https://github.com", "https://kkgithub.com"),
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
                self.output.warning(f"  download failed from {mirror_url}: {e}")
                continue
        raise last_err

    def _download_deps(self):
        """Pre-download FetchContent dependencies to local mirror directory.

        cmake/deps.txt still uses the same `Name;Url;SHA1` format as 1.27.1, so
        the parser below is unchanged.  Names verified against the 1.29.1
        deps.txt (flatbuffers/onnx/eigen/re2/... still present).
        """
        mirror = self._get_mirror_dir()
        deps_file = self._get_source_dir() / "cmake" / "deps.txt"

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
        """Build protoc from protobuf source for the host platform."""
        mirror = self._get_mirror_dir()
        proto_zip = mirror / "github.com" / "protocolbuffers" / "protobuf" / "archive" / "refs" / "tags" / "v21.12.zip"

        if not proto_zip.exists():
            self.output.info("Protobuf not in mirror, downloading directly...")
            proto_zip.parent.mkdir(parents=True, exist_ok=True)
            url = "https://github.com/protocolbuffers/protobuf/archive/refs/tags/v21.12.zip"
            tmp_path = proto_zip.with_suffix(".tmp")
            self._download_with_mirrors(url, str(tmp_path))
            shutil.move(str(tmp_path), str(proto_zip))
            self.output.info(f"Downloaded protobuf: {proto_zip.stat().st_size} bytes")

        proto_build_dir = Path(self.build_folder) / "protobuf-protoc"
        proto_build_dir.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(proto_zip) as zf:
            zf.extractall(proto_build_dir)

        proto_src = proto_build_dir / "protobuf-21.12"

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
            "-j", str(os.cpu_count() or 1),
        ], check=True)

        protoc_path = build_dir / "protoc"
        if not protoc_path.exists():
            candidates = list(build_dir.glob("protoc-*"))
            if not candidates:
                raise RuntimeError(f"protoc binary not found in {build_dir}")
            protoc_path = candidates[0]

        self.output.info(f"Built protoc at {protoc_path}")
        return str(protoc_path)

    def _patch_mlas_cmake(self):
        """Enable BF16+FP16 for the whole onnxruntime_mlas target.

        mlasi.h exposes `bfloat16_t` members whenever `__ARM_FEATURE_BF16` is
        visible, so the per-file `set_source_files_properties(... -march=...)`
        lines that upstream applies to a handful of kernels are not enough for
        every translation unit of the target.

        This used to be conandata patch 0002.  The patch engine (patch-ng)
        rejected the hunk against the 1.29.1 tree ("hunk no.1 doesn't match
        source file at line 598"), so the change is applied here as an
        idempotent in-place edit instead — same content, no dependence on the
        patch tool's hunk matching.

        `onnxruntime_mlas` is created near the top of the file (line 20 in
        1.29.1), well before the insertion point, so target_compile_options()
        is valid here.
        """
        mlas_cmake = self._get_source_dir() / "cmake" / "onnxruntime_mlas.cmake"
        if not mlas_cmake.exists():
            self.output.warning("onnxruntime_mlas.cmake not found, skipping BF16/FP16 patch")
            return

        content = mlas_cmake.read_text()
        marker = "target_compile_options(onnxruntime_mlas PRIVATE -march=armv8.2-a+bf16+fp16)"
        if marker in content:
            self.output.info("onnxruntime_mlas.cmake already carries the BF16/FP16 flags")
            return

        anchor = (
            '          set_source_files_properties(${MLAS_SRC_DIR}/erf_neon_fp16.cpp '
            'PROPERTIES COMPILE_FLAGS " -march=armv8.2-a+fp16 ")\n'
            '          set_source_files_properties(${MLAS_SRC_DIR}/gelu_neon_fp16.cpp '
            'PROPERTIES COMPILE_FLAGS " -march=armv8.2-a+fp16 ")\n'
            "        endif()\n"
        )
        # Insert ahead of the closing endif(), not after it.
        replacement = anchor.replace(
            "        endif()\n",
            "          # OHOS: enable BF16+FP16 for the whole MLAS target.  mlasi.h exposes\n"
            "          # bfloat16_t members whenever __ARM_FEATURE_BF16 is visible, so the\n"
            "          # per-file flags above are not sufficient for every translation unit.\n"
            f"          {marker}\n"
            "        endif()\n",
        )

        if anchor not in content:
            self.output.warning(
                "onnxruntime_mlas.cmake: expected anchor (erf/gelu neon_fp16 flags) not "
                "found — BF16/FP16 flags NOT applied"
            )
            return

        mlas_cmake.write_text(content.replace(anchor, replacement, 1))
        self.output.info("Patched onnxruntime_mlas.cmake with BF16/FP16 target flags")

    def _patch_cpuinfo(self):
        """Patch the FetchContent-extracted cpuinfo to recognize OHOS as Linux.

        The upstream rule (onnxruntime_external_deps.cmake:378-397) only applies
        its Linux sysfs handling under `CMAKE_SYSTEM_NAME STREQUAL "Linux"`;
        OHOS falls through to the bare else().  Because cpuinfo arrives via
        FetchContent, a normal conandata patch cannot reach it, so this runs
        after configure has populated _deps/.
        """
        build_dir = Path(self.build_folder)
        cpuinfo_cmake = build_dir / "_deps" / "pytorch_cpuinfo-src" / "CMakeLists.txt"

        if not cpuinfo_cmake.exists():
            self.output.warning("cpuinfo CMakeLists.txt not found, skipping patch")
            return

        content = cpuinfo_cmake.read_text()
        if "OHOS" in content:
            self.output.info("cpuinfo already patched for OHOS")
            return

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
            self.output.warning("cpuinfo patch had no effect (patterns not found)")
        else:
            cpuinfo_cmake.write_text(content)
            self.output.info("Patched cpuinfo CMakeLists.txt for OHOS")
