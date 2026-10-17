from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (
    apply_conandata_patches,
    collect_libs,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.layout import basic_layout
import gzip
import hashlib
import os
import re
import tarfile


class ApacheArrowConan(ConanFile):
    name = "apache-arrow"
    version = "25.0.0"
    description = "Apache Arrow C++ — cross-language development platform for in-memory data"
    license = "Apache-2.0"
    homepage = "https://arrow.apache.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def configure(self):
        # Arrow 25.0.0 强制要求 C++20（SetupCxxFlags.cmake:173-180，低于 20 直接
        # FATAL_ERROR），CI profile 默认 cppstd=17，必须覆盖。
        self.settings.compiler.cppstd = "20"

    def export_sources(self):
        export_conandata_patches(self)
        # xsimd 必须随配方交付：Conan 执行 build() 时 recipe_folder 指向缓存副本
        # （p/<pkg>/e），未在 export_sources 中声明的文件不在那里。
        # 以**纯文本目录**而不是归档交付，见 _prepare_vendored_xsimd()。
        copy(self, "*",
             src=os.path.join(self.recipe_folder, "vendored-xsimd-14.2.0"),
             dst=os.path.join(self.export_sources_folder, "vendored-xsimd-14.2.0"))

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # OHOS 处理器兼容：见 patches/0001-setupcxxflags-unknown-processor.patch
        # OHOS 走 CMake 的 unknown Platform 路径，Arrow 的 VERSION/SOVERSION
        # 属性默认不产生 ELF SONAME，由 patches/0002-buildutils-ohos-soname.patch
        # 修复（该补丁同时接受 HarmonyOS 与 OHOS 两种 CMAKE_SYSTEM_NAME）。
        tc.variables["CMAKE_SHARED_LINKER_FLAGS"] = "-Wl,--enable-new-dtags"
        tc.variables["CMAKE_FIND_USE_PACKAGE_REGISTRY"] = "FALSE"
        tc.variables["CMAKE_FIND_USE_SYSTEM_PACKAGE_REGISTRY"] = "FALSE"
        tc.variables["ARROW_RPATH_ORIGIN"] = "OFF"
        tc.variables["ARROW_INSTALL_NAME_RPATH"] = "OFF"
        # Arrow 自身的 SIMD 派发关闭（OHOS clang 无调优基线）；
        # 注意这并不会去掉 xsimd 依赖，见下面的说明。
        tc.variables["ARROW_SIMD_LEVEL"] = "NONE"
        tc.variables["ARROW_RUNTIME_SIMD_LEVEL"] = "NONE"
        # ── 核心模块（第一阶段最小可用：Array/Builder/Table/Schema + IPC + IO）
        tc.variables["ARROW_BUILD_TESTS"] = "OFF"
        tc.variables["ARROW_BUILD_SHARED"] = "ON" if self.options.shared else "OFF"
        tc.variables["ARROW_BUILD_STATIC"] = "OFF" if self.options.shared else "ON"
        tc.variables["ARROW_IPC"] = "ON"
        tc.variables["ARROW_COMPUTE"] = "ON"
        tc.variables["ARROW_CSV"] = "ON"
        tc.variables["ARROW_FILESYSTEM"] = "ON"
        # ARROW_JSON 会在 ThirdpartyToolchain.cmake:410-412 自动要求
        # RapidJSON（FetchContent 下载）。第一阶段最小可用不含 JSON。
        tc.variables["ARROW_JSON"] = "OFF"
        # ── 关闭非核心重型模块
        tc.variables["ARROW_MIMALLOC"] = "OFF"
        tc.variables["ARROW_JEMALLOC"] = "OFF"
        tc.variables["ARROW_FLIGHT"] = "OFF"
        tc.variables["ARROW_DATASET"] = "OFF"
        tc.variables["ARROW_PARQUET"] = "OFF"
        tc.variables["ARROW_ORC"] = "OFF"
        tc.variables["ARROW_GANDIVA"] = "OFF"
        tc.variables["ARROW_CUDA"] = "OFF"
        tc.variables["ARROW_BUILD_EXAMPLES"] = "OFF"
        tc.variables["ARROW_BUILD_BENCHMARKS"] = "OFF"
        # ── 外部依赖：构建期零网络
        # xsimd：ThirdpartyToolchain.cmake:2848-2855 无条件 requires >= 14.2.0
        #   （ARROW_SIMD_LEVEL=NONE 并不会跳过它），header-only。
        #   它由 build_xsimd() 的 externalproject_add() 构建（:2830-2835），
        #   源码来自 URL 下载而不是 FetchContent —— 所以必须用 ARROW_XSIMD_URL
        #   环境变量把它指向配方随附的 tarball（见 _prepare_vendored_xsimd()）。
        #   注意：FETCHCONTENT_SOURCE_DIR_XSIMD 对它完全无效，早期版本曾误用它。
        tc.variables["ARROW_DEPENDENCY_SOURCE"] = "SYSTEM"
        tc.variables["xsimd_SOURCE"] = "BUNDLED"
        # ── 压缩/正则等可选依赖一律关闭（本阶段不引入）
        tc.variables["ARROW_WITH_RE2"] = "OFF"
        tc.variables["ARROW_WITH_UTF8PROC"] = "OFF"
        tc.variables["ARROW_WITH_ZLIB"] = "OFF"
        tc.variables["ARROW_WITH_ZSTD"] = "OFF"
        tc.variables["ARROW_WITH_LZ4"] = "OFF"
        tc.variables["ARROW_WITH_SNAPPY"] = "OFF"
        tc.variables["ARROW_WITH_BROTLI"] = "OFF"
        tc.variables["ARROW_WITH_BZ2"] = "OFF"
        tc.generate()

    def _apply_file_io_edge_cases(self):
        """Apply the `0003-ohos-file-io-edge-cases` change in place.

        The same edit is declared in conandata.yml as a unified diff，但 OHOS
        构建机上的 Conan 用 patch-ng 应用补丁，其 hunk 匹配拒绝了这一 hunk——
        而在干净的 25.0.0 源码树上 GNU patch 与 toybox patch 都能干净应用
        （落在 file.cc:274，偏移 6 行）。这里改为幂等的文本替换，改动内容与
        统一 diff 完全一致，同时去掉对该工具行为的依赖。

        两处改动都保持 Arrow 自身的契约语义：
          1. arrow/io/file.cc —— 在向 OS 请求预读建议前跳过零长度 range
             （零长度 ReadRange 语义上就是空）。
          2. arrow/filesystem/localfs.cc —— 拒绝以 '/' 结尾的写路径，
             直接报 IOError，而不是产出一个稍后才失败的流。
        """
        edits = [
            (
                "cpp/src/arrow/io/file.cc",
                "      RETURN_NOT_OK(internal::ValidateRange(range.offset, range.length));\n"
                "#if defined(POSIX_FADV_WILLNEED)\n"
                "      int ret = posix_fadvise(fd_.fd(), range.offset, range.length, POSIX_FADV_WILLNEED);",
                "      RETURN_NOT_OK(internal::ValidateRange(range.offset, range.length));\n"
                "#if defined(POSIX_FADV_WILLNEED)\n"
                "      // A zero-length ReadRange is empty; skip the read-ahead advice.\n"
                "      if (range.length == 0) {\n"
                "        continue;\n"
                "      }\n"
                "      int ret = posix_fadvise(fd_.fd(), range.offset, range.length, POSIX_FADV_WILLNEED);",
            ),
            (
                "cpp/src/arrow/filesystem/localfs.cc",
                "  RETURN_NOT_OK(ValidatePath(path));\n"
                "  ARROW_ASSIGN_OR_RAISE(auto fn, PlatformFilename::FromString(path));",
                "  RETURN_NOT_OK(ValidatePath(path));\n"
                "  // Output streams target files, not directories.\n"
                "  if (!path.empty() && path.back() == '/') {\n"
                '    return Status::IOError("Cannot open for writing: path \'", path, "\' is a directory");\n'
                "  }\n"
                "  ARROW_ASSIGN_OR_RAISE(auto fn, PlatformFilename::FromString(path));",
            ),
        ]
        for rel, needle, replacement in edits:
            target = os.path.join(self.source_folder, rel)
            with open(target, encoding="utf-8") as fh:
                text = fh.read()
            if replacement in text:
                self.output.info(f"{rel}: already applied")
                continue
            if needle not in text:
                raise ConanException(f"{rel}: expected anchor not found")
            with open(target, "w", encoding="utf-8") as fh:
                fh.write(text.replace(needle, replacement, 1))
            self.output.info(f"{rel}: applied")

    def _fix_xsimd_sve_probe(self, xsimd_dir):
        """Make xsimd 14.2.0's SVE probe compile with the OHOS NDK clang.

        xsimd detects the SVE vector length with an SVE instruction:

            __attribute__((target("arch=armv8-a+sve")))
            inline arm_reg64_t arm_rdvl_unsafe() { __asm__ volatile("rdvl %0, #1" ...); }

        The OHOS NDK's clang 15 does not recognise `armv8-a+sve` in the target
        attribute and drops the attribute instead of failing:

            warning: unknown architecture 'armv8-a+sve' in the 'target' attribute
                     string; 'target' attribute ignored [-Wignored-attributes]
            error: instruction requires: sve or sme

        so every translation unit that includes xsimd fails to build (first seen
        in arrow/util/cpu_info.cc).  This is independent of our own flags — the
        probe above fails the same way with and without -march.

        `target("sve")` names the feature directly, which this clang does
        accept, and is equivalent here: the default arch is already armv8-a, so
        the only extra feature the function needs is SVE.  Runtime detection
        (hwcap) and the semantics of arm_cpu_features::sve() are unchanged — on
        a target whose compiler cannot emit SVE this correctly reports no SVE.
        """
        header = os.path.join(xsimd_dir, "include", "xsimd", "config",
                              "xsimd_cpu_features_arm.hpp")
        if not os.path.exists(header):
            raise ConanException(f"vendored xsimd header missing: {header}")
        old = '__attribute__((target("arch=armv8-a+sve")))'
        new = '__attribute__((target("sve")))'
        with open(header, encoding="utf-8") as fh:
            text = fh.read()
        if new in text:
            self.output.info("xsimd SVE probe: already adapted")
            return
        if old not in text:
            raise ConanException(
                f"xsimd SVE probe: expected anchor not found in {header}")
        with open(header, "w", encoding="utf-8") as fh:
            fh.write(text.replace(old, new, 1))
        self.output.info("xsimd SVE probe: target attribute adapted for OHOS clang")

    def _prepare_vendored_xsimd(self):
        """Deliver xsimd 14.2.0 from the recipe, with the OHOS SVE fix applied.

        Arrow builds xsimd through `externalproject_add(xsimd_ep ... URL ...)`
        (ThirdpartyToolchain.cmake:2830-2835).  The source therefore comes from
        a *download*, not from FetchContent, and the URL is taken from the
        ARROW_XSIMD_URL environment variable when it is set (:813-819) — that is
        the only supported way to point it at a local file.  The download is
        checksum-verified against ARROW_XSIMD_BUILD_SHA256_CHECKSUM, which lives
        in cpp/thirdparty/versions.txt, so that entry has to be updated to match
        the tarball we hand over.

        The sources are shipped as plain text and repacked here (not shipped
        pre-patched) so the recipe keeps the byte-exact upstream 14.2.0 tree
        and the one-line OHOS adaptation stays visible in
        _fix_xsimd_sve_probe().

        Why plain text rather than a shipped .tar.gz: a GitCode PR .diff carries
        no binary payload, so a vendored archive makes CI's checkout-pr step
        fail with "missing binary patch data" before Conan ever runs.  The
        binary form was never a build requirement — only the repacked archive
        handed to Arrow's ExternalProject is.

        Note: conan.tools.files.untargz does not exist in the Conan 2.29 on the
        build host (ImportError), hence the stdlib tarfile.
        """
        src_tree = os.path.join(self.export_sources_folder, "vendored-xsimd-14.2.0")
        if not os.path.isdir(src_tree):
            src_tree = os.path.join(self.recipe_folder, "vendored-xsimd-14.2.0")
        if not os.path.isdir(src_tree):
            raise ConanException(
                f"vendored xsimd sources missing in both export_sources "
                f"and the recipe dir: {src_tree}")

        dest = os.path.join(self.build_folder, "_vendored")
        xsimd_dir = os.path.join(dest, "xsimd-14.2.0")
        os.makedirs(xsimd_dir, exist_ok=True)
        copy(self, "*", src=src_tree, dst=xsimd_dir)
        self._fix_xsimd_sve_probe(xsimd_dir)

        # Repack with the same single top-level directory, so ExternalProject's
        # extraction strips it exactly like the upstream archive.  The archive
        # is built deterministically (fixed entry order, mtime, ownership,
        # modes and gzip mtime) so the sha256 recorded in versions.txt below is
        # reproducible across builds and machines.
        repacked = os.path.join(dest, "xsimd-14.2.0-ohos.tar.gz")
        self._write_deterministic_tarball(repacked, xsimd_dir, "xsimd-14.2.0")
        with open(repacked, "rb") as fh:
            sha = hashlib.sha256(fh.read()).hexdigest()

        versions = os.path.join(self.source_folder, "cpp", "thirdparty", "versions.txt")
        key = "ARROW_XSIMD_BUILD_SHA256_CHECKSUM="
        with open(versions, encoding="utf-8") as fh:
            text = fh.read()
        updated = re.sub(rf"(?m)^{re.escape(key)}.*$", key + sha, text)
        if updated == text and key + sha not in text:
            raise ConanException(f"{versions}: {key.strip('=')} line not found")
        with open(versions, "w", encoding="utf-8") as fh:
            fh.write(updated)

        # Read by Arrow's cmake at configure time.
        os.environ["ARROW_XSIMD_URL"] = repacked
        self.output.info(
            f"vendored xsimd repacked for OHOS: {repacked} (sha256 {sha[:16]}...)")

    @staticmethod
    def _write_deterministic_tarball(path, src_dir, arc_root):
        """Write `src_dir` into `path` as a byte-reproducible .tar.gz.

        Every input that would otherwise vary between runs is pinned:
        entry order (depth-then-name, parents before children), mtime, uid/gid,
        uname/gname, modes, and the gzip header timestamp.  The gzip filename
        field is cleared for the same reason.
        """
        entries = []
        for root, dirs, files in os.walk(src_dir):
            dirs.sort()
            for name in dirs + sorted(files):
                full = os.path.join(root, name)
                rel = os.path.relpath(full, src_dir).replace(os.sep, "/")
                entries.append((rel, full))
        # parents before children, then lexical order
        entries.sort(key=lambda e: (e[0].count("/"), e[0]))

        def normalise(ti):
            ti.uid = ti.gid = 0
            ti.uname = ti.gname = ""
            ti.mtime = 0
            ti.mode = 0o755 if ti.isdir() else 0o644
            return ti

        with open(path, "wb") as raw:
            with gzip.GzipFile(filename="", mode="wb", compresslevel=9,
                               fileobj=raw, mtime=0) as gz:
                with tarfile.open(fileobj=gz, mode="w",
                                  format=tarfile.GNU_FORMAT) as tf:
                    for rel, full in entries:
                        ti = normalise(tf.gettarinfo(full, arcname=f"{arc_root}/{rel}"))
                        if ti.isdir():
                            tf.addfile(ti)
                        else:
                            with open(full, "rb") as fh:
                                tf.addfile(ti, fh)

    def build(self):
        apply_conandata_patches(self)
        self._apply_file_io_edge_cases()
        # Arrow 的 cmake 无条件解析 xsimd >= 14.2.0（ThirdpartyToolchain.cmake:
        # 2848-2855），ARROW_SIMD_LEVEL 并不能关掉它。xsimd 是 header-only，
        # 由本配方随附并在此处重打包交付，构建期零网络。
        self._prepare_vendored_xsimd()

        cmake = CMake(self)
        # CMakeLists.txt 在解压后的 cpp/ 子目录中
        cmake.configure(build_script_folder=os.path.join(self.source_folder, "cpp"))
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = collect_libs(self)
        self.cpp_info.set_property("cmake_file_name", "Arrow")
        self.cpp_info.set_property("cmake_target_name", "Arrow::arrow")
        alias = "Arrow::arrow_shared" if self.options.shared else "Arrow::arrow_static"
        self.cpp_info.set_property("cmake_target_aliases", [alias])

        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]
