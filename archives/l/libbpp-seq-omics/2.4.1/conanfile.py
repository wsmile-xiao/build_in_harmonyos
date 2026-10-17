#!/usr/bin/env python3
"""Conan recipe — libbpp-seq-omics 2.4.1 (CMake).

Bio++ Sequence Omics：在 bpp-seq 之上提供 MAF/FASTQ/GFF 等 omics 格式的
读写与统计，是 Bio++ 家族中只依赖 bpp-seq 的一环。

上游构建两个目标：`bpp-seq-omics-static`（STATIC）与 `bpp-seq-omics-shared`（SHARED，
OUTPUT_NAME 均为 `bpp-seq-omics`，SOVERSION=12）；`test/` 下 14 个 `.cpp` 各自编译成
独立程序并经 `add_test` 注册到 `enable_testing()` 的 ctest 套件。本配方在
`build()` 里构建并运行完整上游 ctest 套件后才打包。

依赖：上游 `find_package (bpp-seq 12.0.0 REQUIRED)`。
**与同族先例 libbpp-seq 的关键差异**：libbpp-seq 写配方时 `libbpp-core/2.4.1`
尚未发布到 ohpcd，只能把 bpp-core 源码 vendor 进构建目录；**现在
`libbpp-seq/2.4.1` 与其合并打包的 bpp-core 都已发布到制品仓**，因此本配方
直接声明 `requires("libbpp-seq/2.4.1")`，不再 vendor —— 依赖图干净、preflight
可查、消费者语义正确。

沿用的同族结论（先例逐条踩过）：
* `cmake_minimum_required(2.8.11)` 需 `CMAKE_POLICY_VERSION_MINIMUM=3.5`。
* 上游同时构建 static/shared 双目标，`BUILD_SHARED_LIBS` 无法二选一；两者都打包，
  由 `package()` 按 `shared` 选项裁掉消费者用不到的那一套。
* Conan 包名用 `libbpp-seq-omics` 前缀，避免 CMakeDeps 生成的
  `libbpp-seq-omics-config.cmake` 遮蔽上游 `bpp-seq-omics-config.cmake`
  （下游模块要靠后者做 `find_package(bpp-seq-omics CONFIG)`）。
* 上游包配置装在 `lib/cmake/bpp-seq`，而 CMakeDeps 只会生成
  `libbpp-seq-config.cmake`；`find_package(bpp-seq 12.0.0)` 因此**必须**由
  `<dep>/lib/cmake/bpp-seq` 提供，本配方在 `generate()` 里显式注入
  `bpp-seq_DIR`（同时兜底 `CMAKE_PREFIX_PATH`）。

交叉编译时（本机 x86_64 → OHOS）ctest 无法在构建宿主上执行，此时只构建不运行；
官方 CI 是设备原生构建，2 个上游用例会真实执行。
"""

import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)

# 上游 test/ 下 2 个 .cpp（v2.4.1 现场清点）。用于校验 ctest 真的跑全了。
UPSTREAM_TESTS = (
    "test_fastq", "test_gff",
)


class LibbppSeqOmicsConan(ConanFile):
    name = "libbpp-seq-omics"
    version = "2.4.1"
    description = "Bio++ Sequence Omics: MAF/FASTQ/GFF handling on top of bpp-seq"
    license = "CECILL-2.1"
    homepage = "https://github.com/BioPP/bpp-seq-omics"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # bpp-seq-omics 的公开头文件包含 Bpp/Seq 头，消费者编译时会用到；
        # libbpp-seq/2.4.1 的包内已合并 bpp-core 的库与 CMake 配置。
        self.requires("libbpp-seq/2.4.1",
                      transitive_headers=True, transitive_libs=True)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.cache_variables["CMAKE_POSITION_INDEPENDENT_CODE"] = (
            bool(self.options.shared)
            or bool(self.options.get_safe("fPIC", True)))
        # 上游 test/ 经 BUILD_TESTING 注册 14 个 ctest 用例。
        tc.cache_variables["BUILD_TESTING"] = True
        # 上游声明 cmake_minimum_required(VERSION 2.8.11)。
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # ★ 交叉编译关键：上游 src/CMakeLists 直接 `set(CMAKE_CXX_FLAGS "-std=c++11 ...")`，
        # 会把 Conan Toolchain 注入的 --target/--sysroot **整个覆盖掉**，于是 clang
        # 按宿主编译、**静默产出宿主架构产物**（静态库不报错，共享库一链接才报
        # "incompatible with aarch64linux"）。实测：--target 放在 CMAKE_CXX_FLAGS 里会被覆盖。
        # 改用 CMAKE_<LANG>_COMPILER_TARGET / CMAKE_SYSROOT —— CMake 对 Clang 会据此
        # 自行加 --target，且上游的 set() 碰不到它们（已用最小 CMake 工程对照验证）。
        # 原生构建（设备上 build==host）下 profile 不设这些 flag，此段自动为空。
        cxxflags = self.conf.get("tools.build:cxxflags", default=[], check_type=list) or []
        cflags = self.conf.get("tools.build:cflags", default=[], check_type=list) or []
        target = next((f.split("=", 1)[1] for f in (cxxflags + cflags)
                       if f.startswith("--target=")), None)
        sysroot = next((f.split("=", 1)[1] for f in (cxxflags + cflags)
                        if f.startswith("--sysroot=")), None)
        if target:
            tc.cache_variables["CMAKE_C_COMPILER_TARGET"] = target
            tc.cache_variables["CMAKE_CXX_COMPILER_TARGET"] = target
            self.output.info(
                f"upstream overwrites CMAKE_CXX_FLAGS; injecting target via "
                f"CMAKE_<LANG>_COMPILER_TARGET={target}")
        if sysroot:
            tc.cache_variables["CMAKE_SYSROOT"] = sysroot
        tc.cache_variables["CMAKE_INSTALL_RPATH"] = "$ORIGIN"
        seq_dir = self._bpp_seq_cmake_dir()
        if seq_dir:
            # find_package(bpp-seq 12.0.0 REQUIRED) 只能靠上游包配置满足：
            # CMakeDeps 生成的 libbpp-seq-config.cmake 名字对不上。
            tc.cache_variables["bpp-seq_DIR"] = seq_dir
            # bpp-seq-config.cmake 内部会 find_package(bpp-core)，同样要走已修正的导出。
            core_dir = getattr(self, "_shim_core_dir", None)
            if core_dir:
                tc.cache_variables["bpp-core_DIR"] = core_dir
            self.output.info(
                f"bpp-seq CMake package dir: {seq_dir} (bpp-core: {core_dir})")
        else:
            self.output.warning(
                "bpp-seq CMake package dir not found in the dependency package; "
                "find_package(bpp-seq) will fall back to CMake's own search paths")
        tc.generate()
        CMakeDeps(self).generate()

    def _bpp_seq_cmake_dir(self):
        """定位依赖包内上游 bpp-seq-config.cmake 所在目录（经 shim 修正后）。"""
        shim = self._prepare_cmake_shim()
        if not shim:
            return None
        preferred = os.path.join(shim, "lib", "cmake", "bpp-seq")
        if os.path.isfile(os.path.join(preferred, "bpp-seq-config.cmake")):
            # 让内层 find_package(bpp-core) 也走同一份已修正的导出
            self._set_bpp_core_dir(os.path.join(shim, "lib", "cmake", "bpp-core"))
            return preferred.replace("\\", "/")
        for root, _dirs, files in os.walk(shim):
            if "bpp-seq-config.cmake" in files:
                return root.replace("\\", "/")
        return None

    def _set_bpp_core_dir(self, path):
        if os.path.isfile(os.path.join(path, "bpp-core-config.cmake")):
            self._shim_core_dir = path.replace("\\", "/")

    def _prepare_cmake_shim(self):
        """把依赖包复制到构建目录，并修掉其 CMake 导出文件里指向已裁剪 .so 的 shared 目标。

        libbpp-seq/2.4.1 打包时按 shared=False 裁掉了 *.so，但它的 CMake 导出
        文件（bpp-core-targets*.cmake / bpp-seq-targets*.cmake）仍把
        `bpp-core-shared` / `bpp-seq-shared` 列为 imported target 并指向不存在的
        .so。CMake 的 import check 会在下游 `find_package(bpp-seq)` 时直接报
        "references the file ... but this file does not exist" 而 configure 失败。

        这里**不改依赖缓存**，只在本次构建内复制一份包、剔除 shared 目标，再把
        `bpp-seq_DIR` / `bpp-core_DIR` 指过去。整包复制是为了保持
        `${_IMPORT_PREFIX}`（config 文件上溯三级）与 .a / 头文件的相对位置不变。
        """
        dep = self.dependencies["libbpp-seq"]
        source = getattr(dep, "package_folder", None)
        if not source:
            return None
        shim = os.path.join(self.build_folder, "libbpp-seq-shim")
        if os.path.isdir(shim):
            shutil.rmtree(shim, ignore_errors=True)
        shutil.copytree(source, shim)
        stripped = 0
        for name in ("bpp-core", "bpp-seq"):
            directory = os.path.join(shim, "lib", "cmake", name)
            if not os.path.isdir(directory):
                continue
            for entry in os.listdir(directory):
                if not entry.endswith(".cmake"):
                    continue
                path = os.path.join(directory, entry)
                if entry == f"{name}-config.cmake":
                    # config 文件自己也直接 get_property(TARGET <name>-shared)，
                    # 目标被移除后该行会报 "has not been created"，必须一并去掉。
                    if self._strip_shared_from_config(path, name):
                        stripped += 1
                elif entry.startswith(f"{name}-targets"):
                    if self._strip_shared_target(path, name):
                        stripped += 1
        self.output.info(
            f"cmake shim: copied dependency package to {shim}, "
            f"stripped shared targets in {stripped} export file(s); "
            f"dependency package itself is not modified")
        return shim

    @staticmethod
    def _strip_shared_from_config(path, name):
        """修掉 config 文件里对 <name>-shared 目标的直接引用。

        bpp-core-config.cmake / bpp-seq-config.cmake 会做
        `get_property (shared-location TARGET <name>-shared PROPERTY LOCATION)`；
        该 imported target 被移除后，这一行会让 find_package() 直接报
        "Target ... has not been created"，必须删掉。

        但 `set (BPP_LIBS_SHARED ... <name>-shared)` **不能删**：上游
        src/CMakeLists 用 `${BPP_LIBS_SHARED}` 给 shared 库目标链接依赖，
        删空后 shared 目标就拿不到依赖的 INTERFACE include 路径，
        表现为编译时报 `Bpp/Exceptions.h` 找不到（实测：static 目标有 include
        而 shared 目标没有）。因此把它**重定向到 static 目标** —— 两个静态归档
        都是 PIC（依赖包 fPIC=True），可安全链进共享库。
        """
        with open(path, encoding="utf-8") as handle:
            lines = handle.readlines()
        kept = [line for line in lines if f"TARGET {name}-shared" not in line]
        kept = [line.replace(f"{name}-shared", f"{name}-static") for line in kept]
        if kept != lines:
            with open(path, "w", encoding="utf-8", newline="\n") as handle:
                handle.writelines(kept)
            return True
        return False

    @staticmethod
    def _strip_shared_target(path, name):
        """从一份 CMake 导出文件里移除 <name>-shared 目标及其 import check 项。"""
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        original = text
        # 1) expected/check 列表：IN ITEMS <name>-static <name>-shared)
        text = re.sub(rf"(\bIN ITEMS\s+{re.escape(name)}-static)\s+{re.escape(name)}-shared\)",
                      r"\1)", text)
        # 2) "# Create imported target <name>-shared" + add_library + set_target_properties 块
        text = re.sub(
            rf'# Create imported target {re.escape(name)}-shared\n.*?\n\)\n',
            "", text, flags=re.S)
        # 3) release 文件里的 "# Import target \"<name>-shared\"" 块
        text = re.sub(
            rf'# Import target "{re.escape(name)}-shared".*?list\(APPEND _cmake_import_check_files_for_{re.escape(name)}-shared[^\n]*\n',
            "", text, flags=re.S)
        if text != original:
            with open(path, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(text)
            return True
        return False

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._dump_elf_info(os.path.join(self.build_folder, "src", "libbpp-seq-omics.so"),
                            "build-tree libbpp-seq-omics")
        self._run_upstream_tests()

    # ── 工具解析（同族先例：裸 subprocess 拿不到 Conan 聚合 buildenv）──────

    def _cmake_bin(self):
        try:
            conf_path = self.conf.get("user.hmbs:cmake_path", default=None, check_type=str)
        except Exception:
            conf_path = None
        for candidate in (conf_path, os.environ.get("HMBS_CMAKE"),
                          os.environ.get("CMAKE")):
            if candidate and os.path.isfile(candidate):
                return candidate
        found = shutil.which("cmake")
        if found:
            return found
        for candidate in ("/data/service/hnp/bin/cmake",
                          "/storage/Users/currentUser/usr/local/bin/cmake",
                          "/usr/local/bin/cmake", "/usr/bin/cmake"):
            if os.path.isfile(candidate):
                return candidate
        self.output.warning("cmake not found via conf/env/PATH/HNP; trying bare 'cmake'")
        return "cmake"

    def _ctest_bin(self):
        sibling = os.path.join(os.path.dirname(self._cmake_bin()), "ctest")
        if os.path.isfile(sibling):
            return sibling
        found = shutil.which("ctest")
        if found:
            return found
        for candidate in ("/data/service/hnp/bin/ctest",
                          "/storage/Users/currentUser/usr/local/bin/ctest",
                          "/usr/local/bin/ctest", "/usr/bin/ctest"):
            if os.path.isfile(candidate):
                return candidate
        self.output.warning("ctest not found via cmake sibling/PATH/HNP; trying bare 'ctest'")
        return "ctest"

    def _dump_elf_info(self, path, tag):
        """把 .so 的 SONAME/DT_NEEDED/RUNPATH 打进日志，便于定位加载失败。不失败构建。"""
        try:
            if not path or not os.path.isfile(path):
                self.output.info(f"elf-info [{tag}]: not found: {path}")
                return
            tool = shutil.which("readelf") or shutil.which("llvm-readelf")
            if tool is None:
                for base in ("/data/service/hnp/bin", "/usr/bin"):
                    for name in ("readelf", "llvm-readelf"):
                        candidate = os.path.join(base, name)
                        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                            tool = candidate
                            break
                    if tool:
                        break
            if tool is None:
                self.output.info(f"elf-info [{tag}]: no readelf tool found")
                return
            proc = subprocess.run([tool, "-d", path], stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT, text=True, timeout=120)
            lines = [l for l in (proc.stdout or "").splitlines()
                     if any(k in l for k in ("SONAME", "NEEDED", "RPATH", "RUNPATH"))]
            self.output.info(f"elf-info [{tag}]:\n" + "\n".join(lines[-20:]))
        except Exception as error:                                # noqa: BLE001
            self.output.info(f"elf-info [{tag}]: skipped ({error})")

    def _ctest_lib_paths(self):
        """ctest 需要的绝对库目录（构建树 shared + 依赖包）。"""
        dirs = []
        for candidate in (
            os.path.join(self.build_folder, "src"),
            os.path.join(self.dependencies["libbpp-seq"].package_folder or "", "lib"),
            os.path.join(self.dependencies["libbpp-seq"].package_folder or "", "lib64"),
        ):
            if candidate and os.path.isdir(candidate) and candidate not in dirs:
                dirs.append(candidate)
        return dirs

    def _run_upstream_tests(self):
        """运行上游 14 个 ctest 用例，输出 HMBS 证据标记。"""
        discovered = len(UPSTREAM_TESTS)
        result_path = os.path.join(self.build_folder, "upstream_test_result.json")
        if not can_run(self):
            upstream = {
                "status": "skipped", "framework": "ctest",
                "command": "ctest --output-on-failure",
                "discovered": discovered, "executed": 0, "passed": 0,
                "failed": 0, "skipped": discovered,
                "reason": "cross-building: can_run() is false",
            }
            self.output.info("HMBS_UPSTREAM_TEST_RESULT="
                             + json.dumps(upstream, ensure_ascii=False))
            self._persist(result_path, upstream)
            return upstream

        ctest_bin = self._ctest_bin()
        env = dict(os.environ)
        lib_dirs = self._ctest_lib_paths()
        if lib_dirs:
            old = env.get("LD_LIBRARY_PATH", "")
            env["LD_LIBRARY_PATH"] = ":".join(lib_dirs) + (":" + old if old else "")
        self.output.info(f"ctest binary: {ctest_bin}; lib dirs: {lib_dirs}")
        proc = subprocess.run([ctest_bin, "--output-on-failure"],
                              cwd=self.build_folder, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, text=True, timeout=3600, env=env)
        output = proc.stdout or ""
        self.output.info(output[-6000:])
        match = re.search(r"(\d+)% tests passed,\s*(\d+) tests failed out of (\d+)", output)
        if match:
            total, failed = int(match.group(3)), int(match.group(2))
            executed, passed = total, total - failed
        else:
            passed = len(re.findall(r"\.\.\.\s*Passed", output))
            failed = len(re.findall(r"\.\.\.\s*(?:Failed|Timeout)", output))
            executed = passed + failed
        if executed == 0:
            raise RuntimeError("upstream ctest produced no test results")
        status = ("passed" if proc.returncode == 0 and failed == 0
                  and executed == discovered else "failed")
        upstream = {
            "status": status, "framework": "ctest",
            "command": "ctest --output-on-failure",
            "discovered": discovered, "executed": executed,
            "passed": passed, "failed": failed, "skipped": 0,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT="
                         + json.dumps(upstream, ensure_ascii=False))
        self._persist(result_path, upstream)
        if status != "passed":
            raise RuntimeError(
                f"upstream ctest failed: executed={executed} passed={passed} failed={failed}")
        return upstream

    def _persist(self, path, payload):
        try:
            with open(path, "w", encoding="utf-8", newline="\n") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
        except OSError as error:
            self.output.warning(f"cannot persist upstream result: {error}")

    def package(self):
        copy(self, "COPYING*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        # 上游总是同时装 static 与 shared；按 shared 选项裁掉消费者用不到的一套，
        # 避免下游误链到在 OHOS 上加载失败的 shared 产物。
        self._prune_unrequested_variant()
        self._dump_elf_info(os.path.join(self.package_folder, "lib", "libbpp-seq-omics.so"),
                            "installed libbpp-seq-omics")
        # 把上游 ctest 证据随包发布，命中缓存跳过 build() 时 test_package 仍能复述。
        copy(self, "upstream_test_result.json", src=self.build_folder,
             dst=os.path.join(self.package_folder, "res"), keep_path=False)

    def _prune_unrequested_variant(self):
        import glob
        patterns = (("*.so", "*.so.*"),) if not self.options.shared else (("*.a",),)
        for libdir in (os.path.join(self.package_folder, "lib"),
                       os.path.join(self.package_folder, "lib64")):
            if not os.path.isdir(libdir):
                continue
            for group in patterns:
                for pattern in group:
                    for victim in glob.glob(os.path.join(libdir, pattern)):
                        try:
                            os.remove(victim)
                            self.output.info(
                                f"package: pruned {os.path.basename(victim)}")
                        except OSError as error:
                            self.output.warning(f"package: cannot prune {victim} ({error})")

    def package_info(self):
        self.cpp_info.libs = ["bpp-seq-omics"]
        # 保留上游 bpp-seq-omics-config.cmake 的查找语义，故 Conan 侧改用 libbpp-seq-omics 名。
        self.cpp_info.set_property("cmake_file_name", "libbpp-seq-omics")
        self.cpp_info.set_property("cmake_target_name", "libbpp-seq-omics::libbpp-seq-omics")
        self.cpp_info.set_property("pkg_config_name", "libbpp-seq-omics")
        self.cpp_info.requires = ["libbpp-seq::libbpp-seq"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs.append("m")
